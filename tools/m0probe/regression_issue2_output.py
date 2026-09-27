#!/usr/bin/env python3
"""Bounded Issue #2 Docker-backed output-flood regression; never an M0 qualification run."""

import argparse
import hashlib
import json
import os
import pathlib
import selectors
import signal
import subprocess
import sys
import time

OUTPUT_LIMIT = 1 << 20
STOP_DEADLINE_SECONDS = 10
CASE_DEADLINE_SECONDS = 42
COMMAND_LOG = []
EXPECTED_PROFILE_SHA256 = "34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1"
EXPECTED_ROOTFS_SHA256 = "b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1"
EXPECTED_PROBE_SHA256 = "7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f"
EXPECTED_PROFILE_IMAGE = "sha256:c93dd948b465f2ba26fd1c9f37c540c310424dd07fb74459f50354bf3e6c76f8"


def docker(base, args, timeout=10):
    argv = base + args
    started = time.monotonic()
    try:
        result = subprocess.run(argv, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        COMMAND_LOG.append({"argv": argv, "timed_out": True,
                            "timeout_seconds": timeout,
                            "duration_seconds": time.monotonic() - started})
        raise
    COMMAND_LOG.append({"argv": argv, "exit_status": result.returncode,
                        "duration_seconds": time.monotonic() - started,
                        "stdout_bytes": len(result.stdout),
                        "stderr_bytes": len(result.stderr)})
    if result.returncode:
        raise RuntimeError(f"docker {args[0]} exited {result.returncode}: "
                           f"{result.stderr[:2048]!r}")
    return result.stdout


def kill_client(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Docker CLI process group did not exit after SIGKILL")


def cgroups_for(cid):
    root = pathlib.Path("/sys/fs/cgroup/user.slice")
    uid = os.getuid()
    pattern = f"user-{uid}.slice/user@{uid}.service/**/docker-{cid}.scope"
    try:
        return list(root.glob(pattern))
    except OSError:
        return []


def proc_cgroup_snapshot(pid):
    lines = pathlib.Path(f"/proc/{pid}/cgroup").read_text().splitlines()
    unified = next((line.split("::", 1)[1] for line in lines if "::" in line), None)
    if unified is None or ".." in pathlib.PurePosixPath(unified).parts:
        return {"pid": pid, "cgroup_lines": lines, "host_path": None}
    root = pathlib.Path("/sys/fs/cgroup")
    path = root.joinpath(*pathlib.PurePosixPath(unified).parts[1:])
    if not path.resolve().is_relative_to(root.resolve()):
        return {"pid": pid, "cgroup_lines": lines, "host_path": None,
                "error": "cgroup path escaped the cgroup-v2 root"}
    procs_path = path / "cgroup.procs"
    try:
        procs = procs_path.read_text().split()
    except OSError as exc:
        procs = None
        error = repr(exc)
    else:
        error = None
    return {"pid": pid, "cgroup_lines": lines, "host_path": str(path),
            "host_path_exists": path.exists(), "cgroup_procs": procs,
            "error": error}


def cgroup_current_state(snapshot):
    path = snapshot.get("host_path") if snapshot else None
    if not path:
        return {"observable": False}
    host_path = pathlib.Path(path)
    root = pathlib.Path("/sys/fs/cgroup").resolve()
    if not host_path.resolve().is_relative_to(root):
        return {"observable": False, "error": "recorded cgroup path escaped cgroup root"}
    if not host_path.exists():
        return {"observable": True, "exists": False, "procs": []}
    try:
        procs = (host_path / "cgroup.procs").read_text().split()
    except OSError as exc:
        return {"observable": False, "exists": True, "error": repr(exc)}
    return {"observable": True, "exists": True, "procs": procs}


def build_create_argv(template, image, run_id):
    create = template[3:].copy()
    create[create.index("--name") + 1] = f"drydock-issue2-{run_id}-output"
    create[create.index("--label") + 1] = "drydock.investigation=issue-2"
    image_at = len(create) - 2
    if not create[image_at].startswith("sha256:") or create[image_at + 1] != "output":
        raise RuntimeError("profile create argv is not the archived output probe form")
    create[image_at] = image
    create[image_at:image_at] = ["--label", f"drydock.issue2.run={run_id}"]
    return template[:3] + create


def drain_until_complete(sel, case, started, base, name, cid, captured, total, commands,
                         output_limit=OUTPUT_LIMIT, case_deadline=CASE_DEADLINE_SECONDS,
                         stop_deadline=STOP_DEADLINE_SECONDS):
    """Repaired harness drain_until_complete implementation."""
    reason = None
    stop_proc = None
    stop_started = None
    cancel_seconds = None
    stop_exit_code = None
    stop_completed = False
    cgroup = None
    command = base + ["stop", "--time", "2", name]
    try:
        while sel.get_map() or (stop_proc is not None and stop_proc.poll() is None):
            now = time.monotonic()
            if now - started > case_deadline:
                raise TimeoutError("probe termination exceeded the case deadline")
            if cgroup is None:
                uid = os.getuid()
                root = pathlib.Path("/sys/fs/cgroup/user.slice") / f"user-{uid}.slice" / f"user@{uid}.service"
                matches = list(root.glob("**/docker-" + cid + ".scope"))
                if matches:
                    cgroup = matches[0]
            if stop_proc is not None and stop_proc.poll() is None and now - stop_started >= stop_deadline:
                try:
                    os.killpg(stop_proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                try:
                    stop_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    raise RuntimeError("Docker stop client survived SIGKILL")
                raise subprocess.TimeoutExpired(command, stop_deadline)
            if stop_proc is not None and not stop_completed and stop_proc.poll() is not None:
                cancel_seconds = time.monotonic() - stop_started
                stop_exit_code = stop_proc.returncode
                stop_completed = True
                if stop_exit_code:
                    raise RuntimeError("Docker stop exited " + str(stop_exit_code))
            if reason is None and ((case == "tree" and now - started >= 2) or now - started >= 30 or
                                   (case == "output" and total["seen"] > output_limit)):
                reason = "cancel" if case == "tree" else ("output_limit" if case == "output" and total["seen"] > output_limit else "deadline")
                commands.append(command)
                stop_started = time.monotonic()
                stop_proc = subprocess.Popen(command, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, start_new_session=True)
            if sel.get_map():
                wait_for = .05
                if stop_proc is not None and stop_proc.poll() is None:
                    wait_for = min(wait_for, max(0, stop_started + stop_deadline - time.monotonic()))
                wait_for = min(wait_for, max(0, started + case_deadline - time.monotonic()))
                ready = sel.select(wait_for)
                for key, _ in ready:
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        sel.unregister(key.fileobj)
                        continue
                    remaining = max(0, output_limit - sum(len(value) for value in captured.values()))
                    captured[key.data].extend(data[:remaining])
                    total["seen"] += len(data)
            elif stop_proc is not None and stop_proc.poll() is None:
                wait_for = min(.05, max(0, stop_started + stop_deadline - time.monotonic()))
                wait_for = min(wait_for, max(0, started + case_deadline - time.monotonic()))
                time.sleep(wait_for)
        if stop_proc is not None:
            stop_exit_code = stop_proc.wait(timeout=1)
            if not stop_completed:
                cancel_seconds = time.monotonic() - stop_started
            if stop_exit_code:
                raise RuntimeError("Docker stop exited " + str(stop_exit_code))
        retained = sum(len(value) for value in captured.values())
        return {"termination_reason": reason, "termination_seconds": cancel_seconds,
                "stop_exit_code": stop_exit_code, "cgroup_path": str(cgroup) if cgroup else None,
                "retained_bytes": retained, "truncated": total["seen"] > retained}
    finally:
        if stop_proc is not None and stop_proc.poll() is None:
            try:
                os.killpg(stop_proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                stop_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass


def run_regression(base, template, image, run_id):
    name = f"drydock-issue2-{run_id}-output"
    label = f"drydock.issue2.run={run_id}"
    create_argv = build_create_argv(template, image, run_id)

    row = {
        "name": name,
        "container_create_attempted": False,
        "stop_deadline_seconds": STOP_DEADLINE_SECONDS,
        "output_limit_bytes": OUTPUT_LIMIT,
    }
    owned = False
    proc = None
    commands = []
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    total = {"seen": 0}
    probe_cgroup = None
    started = time.monotonic()

    try:
        owned = True
        row["container_create_attempted"] = True
        docker(base, create_argv[3:])
        inspect = json.loads(docker(base, ["inspect", name]))[0]
        cid = inspect["Id"]
        row["container_id"] = cid
        row["image_id"] = inspect["Image"]
        if inspect["Image"] != image:
            raise RuntimeError("created container image ID differs from requested image")

        proc = subprocess.Popen(base + ["start", "--attach", name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        commands.append(base + ["start", "--attach", name])
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ, "stdout")
        sel.register(proc.stderr, selectors.EVENT_READ, "stderr")

        # Snapshot cgroup when container is active
        probe_pid = int(docker(base, ["inspect", "--format", "{{.State.Pid}}", name]).strip())
        row["probe_pid"] = probe_pid
        if probe_pid > 0:
            probe_cgroup = proc_cgroup_snapshot(probe_pid)
            row["probe_cgroup_live"] = probe_cgroup

        try:
            outcome = drain_until_complete(sel, "output", started, base, name, cid,
                                           captured, total, commands)
        finally:
            sel.close()
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait(timeout=2)
            for stream in (proc.stdout, proc.stderr):
                if stream:
                    stream.close()

        code = proc.wait(timeout=1)
        state = json.loads(docker(base, ["inspect", name]))[0]["State"]
        row["exit_code"] = code
        row["state"] = state
        row["duration_seconds"] = time.monotonic() - started
        row["termination_reason"] = outcome["termination_reason"]
        row["termination_seconds"] = outcome["termination_seconds"]
        row["stop_exit_code"] = outcome["stop_exit_code"]
        row["output_bytes_seen"] = total["seen"]
        row["retained_bytes"] = outcome["retained_bytes"]
        row["truncated"] = outcome["truncated"]
        row["retained_limit_respected"] = outcome["retained_bytes"] <= OUTPUT_LIMIT
        cgroup = outcome["cgroup_path"]
        row["cgroup_path"] = cgroup
        row["docker_commands"] = commands

        # Verify probe passed acceptance criteria
        passed = (
            not state["Running"]
            and outcome["termination_reason"] == "output_limit"
            and outcome["termination_seconds"] is not None
            and outcome["termination_seconds"] <= STOP_DEADLINE_SECONDS
            and outcome["stop_exit_code"] == 0
            and outcome["truncated"] is True
            and outcome["retained_bytes"] <= OUTPUT_LIMIT
            and total["seen"] > OUTPUT_LIMIT
        )
        row["passed"] = passed

    finally:
        if owned:
            try:
                ids = docker(base, ["ps", "-aq", "--no-trunc", "--filter", f"label={label}"]).decode().split()
                row["cleanup_container_ids"] = ids
                row["job_cgroups_before_cleanup"] = {
                    c: [str(p) for p in cgroups_for(c)] for c in ids
                }
                if ids:
                    docker(base, ["rm", "--force", *ids])
                row["cleanup_remove_succeeded"] = True
            except Exception as exc:
                row["cleanup_error"] = repr(exc)

            try:
                cleanup_ids = row.get("cleanup_container_ids", [])
                row["remaining_job_cgroups"] = {
                    c: [str(p) for p in cgroups_for(c)] for c in cleanup_ids
                }
                cid = row.get("container_id")
                if cid and cid not in cleanup_ids:
                    row["remaining_job_cgroups"][cid] = [str(p) for p in cgroups_for(cid)]
                row["probe_cgroup_after_cleanup"] = cgroup_current_state(probe_cgroup)
                remaining = docker(base, ["ps", "-aq", "--no-trunc", "--filter", f"label={label}"]).decode().strip()
                row["remaining_run_containers"] = remaining.splitlines() if remaining else []

                cgroup_after = row["probe_cgroup_after_cleanup"]
                cgroup_remains = cgroup_after.get("observable") and cgroup_after.get("exists") and cgroup_after.get("procs")
                if any(row["remaining_job_cgroups"].values()) or row["remaining_run_containers"] or cgroup_remains:
                    row["cleanup_verification_error"] = "container or job cgroup remains after cleanup"
                else:
                    row["cleanup_verified"] = True
            except Exception as exc:
                row["cleanup_verification_error"] = repr(exc)

    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--rootfs-sha256", required=True)
    parser.add_argument("--probe-sha256", required=True)
    args = parser.parse_args()

    args.output.mkdir(mode=0o700, exist_ok=True)
    run_id = args.output.name.split("-")[2] if "-" in args.output.name else "unknown"

    report = {
        "kind": "issue-2 regression; not an M0 qualification campaign",
        "qualified": False,
        "m0_campaign": False,
        "run_id": run_id,
        "image_requested": args.image,
        "rootfs_sha256": args.rootfs_sha256,
        "probe_sha256": args.probe_sha256,
        "docker_commands": COMMAND_LOG,
    }

    if args.rootfs_sha256 != EXPECTED_ROOTFS_SHA256:
        raise SystemExit(f"rootfs sha256 mismatch: {args.rootfs_sha256}")
    if args.probe_sha256 != EXPECTED_PROBE_SHA256:
        raise SystemExit(f"probe sha256 mismatch: {args.probe_sha256}")

    profile_bytes = args.profile.read_bytes()
    profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
    if profile_sha256 != EXPECTED_PROFILE_SHA256:
        raise SystemExit(f"profile sha256 mismatch: {profile_sha256}")

    profile = json.loads(profile_bytes)
    create_template = next(argv for argv in profile if "create" in argv and argv[-1] == "output")
    base = create_template[:3]

    report["runtime"] = json.loads(docker(base, ["version", "--format", "{{json .}}"]))
    image_inspect = json.loads(docker(base, ["image", "inspect", args.image]))[0]
    report["image_id_observed"] = image_inspect["Id"]
    if report["image_id_observed"] != args.image:
        raise SystemExit("--image must be a content-addressed image ID matching Docker inspect")

    row = run_regression(base, create_template, args.image, run_id)
    report["regression"] = row
    report["status"] = "PASS" if row.get("passed") and row.get("cleanup_verified") else "FAIL"
    report["docker_commands"] = COMMAND_LOG.copy()

    (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
