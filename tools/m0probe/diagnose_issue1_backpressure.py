#!/usr/bin/env python3
"""Bounded Issue #1 Docker attach/stop diagnostic; never a qualification run."""

import argparse
import hashlib
import json
import os
import pathlib
import platform
import selectors
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

RETAIN_LIMIT = 1 << 20
STOP_DEADLINE = 10
CASE_DEADLINE = 45
COMMAND_DEADLINE = 10
COMMAND_LOG = []
EXPECTED_PROFILE_SHA256 = "34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1"
EXPECTED_ROOTFS_SHA256 = "b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1"
EXPECTED_PROBE_SHA256 = "7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f"
EXPECTED_PROFILE_IMAGE = "sha256:c93dd948b465f2ba26fd1c9f37c540c310424dd07fb74459f50354bf3e6c76f8"


def docker(base, args, timeout=COMMAND_DEADLINE):
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


def build_create_argv(template, image, run_id, mode):
    create = template[3:].copy()
    create[create.index("--name") + 1] = f"drydock-issue1-{run_id}-{mode}"
    create[create.index("--label") + 1] = "drydock.investigation=issue-1"
    image_at = len(create) - 2
    if not create[image_at].startswith("sha256:") or create[image_at + 1] != "output":
        raise RuntimeError("profile create argv is not the archived output probe form")
    create[image_at] = image
    create[image_at:image_at] = ["--label", f"drydock.issue1.run={run_id}"]
    return template[:3] + create


def run_case(base, template, image, run_id, mode):
    name = f"drydock-issue1-{run_id}-{mode}"
    label = f"drydock.issue1.run={run_id}"
    create_argv = build_create_argv(template, image, run_id, mode)

    row = {"mode": mode, "name": name, "container_create_attempted": False,
           "stop_deadline_seconds": STOP_DEADLINE, "retained_output_limit": RETAIN_LIMIT}
    owned = False
    attach = None
    stop = None
    reader = None
    release = threading.Event()
    threshold = threading.Event()
    retained = bytearray()
    totals = {"seen": 0}
    reader_errors = []
    failure = None
    probe_cgroup = None

    def drain():
        try:
            with selectors.DefaultSelector() as selector:
                for stream, label_name in ((attach.stdout, "stdout"), (attach.stderr, "stderr")):
                    selector.register(stream, selectors.EVENT_READ, label_name)
                deadline = time.monotonic() + CASE_DEADLINE
                while selector.get_map():
                    if time.monotonic() >= deadline:
                        raise TimeoutError("attachment drain exceeded case deadline")
                    if threshold.is_set() and not release.wait(.05):
                        continue
                    for key, _ in selector.select(.05):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                            continue
                        keep = max(0, RETAIN_LIMIT - len(retained))
                        if keep:
                            retained.extend(data[:keep])
                        totals["seen"] += len(data)
                        if totals["seen"] > RETAIN_LIMIT and not threshold.is_set():
                            threshold.set()
                            row["output_threshold_after_seconds"] = time.monotonic() - started
        except Exception as exc:  # preserved in the result; never interpreted as a pass
            reader_errors.append(repr(exc))

    started = time.monotonic()
    try:
        # Cleanup owns the unique name before create begins, including client timeout.
        owned = True
        row["container_create_attempted"] = True
        docker(base, create_argv[3:])
        inspect = json.loads(docker(base, ["inspect", name]))[0]
        row["container_id"] = inspect["Id"]
        row["image_id"] = inspect["Image"]
        if inspect["Image"] != image:
            raise RuntimeError("created container image ID differs from requested image")
        attach = subprocess.Popen(base + ["start", "--attach", name],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  start_new_session=True)
        row["attach_argv"] = base + ["start", "--attach", name]
        reader = threading.Thread(target=drain, name=f"drain-{mode}", daemon=True)
        reader.start()
        if not threshold.wait(5):
            raise TimeoutError("output threshold not reached within 5 seconds")

        row["output_bytes_before_stop"] = totals["seen"]
        probe_pid = int(docker(base, ["inspect", "--format", "{{.State.Pid}}", name]).strip())
        row["probe_pid"] = probe_pid
        if probe_pid > 0:
            probe_cgroup = proc_cgroup_snapshot(probe_pid)
            row["probe_cgroup_at_output_threshold"] = probe_cgroup
        else:
            row["probe_cgroup_at_output_threshold"] = {"observable": False,
                                                          "reason": "container PID was not running"}
        stop_started = time.monotonic()
        stop = subprocess.Popen(base + ["stop", "--time", "2", name],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        row["stop_argv"] = base + ["stop", "--time", "2", name]
        if mode == "concurrent":
            # Start the stop request while the reader is still at the gate, then
            # release immediately so output continues during the stop operation.
            row["drain_released_after_stop_start"] = True
            row["drain_released_after_seconds"] = time.monotonic() - started
            release.set()
        stop_timed_out = False
        stop_sampled = False
        stop_deadline = stop_started + STOP_DEADLINE
        while stop.poll() is None:
            now = time.monotonic()
            if not stop_sampled and now - stop_started >= 1.0:
                stop_sampled = True
                row["stop_cli_running_at_one_second_sample"] = stop.poll() is None
                try:
                    state = json.loads(docker(
                        base, ["inspect", "--format", "{{json .State}}", name], timeout=1))
                    row["container_state_while_stop_pending"] = state
                    row["probe_cgroup_while_stop_pending"] = cgroup_current_state(probe_cgroup)
                except Exception as exc:
                    row["stop_progress_sample_error"] = repr(exc)
            if now >= stop_deadline and stop.poll() is None:
                stop_timed_out = True
                kill_client(stop)
                break
            time.sleep(.025)
        try:
            if not stop_timed_out:
                stdout, stderr = stop.communicate(timeout=1)
            else:
                stdout, stderr = b"", b""
            if not stop_timed_out:
                row.update(stop_timed_out=False, stop_exit_code=stop.returncode,
                           stop_stdout_bytes=len(stdout), stop_stderr_bytes=len(stderr))
        except subprocess.TimeoutExpired:
            stop_timed_out = True
            row["stop_timed_out"] = True
            kill_client(stop)
        if stop_timed_out:
            row["stop_timed_out"] = True
            row["stop_exit_code"] = None
        row["stop_seconds"] = time.monotonic() - stop_started
        cid = row.get("container_id")
        row["job_cgroups_at_stop_return"] = [str(p) for p in cgroups_for(cid)] if cid else []
        if not row["stop_timed_out"]:
            state = json.loads(docker(base, ["inspect", "--format", "{{json .State}}", name]))
            row["container_state_after_stop"] = state
        release.set()
        try:
            attach_code = attach.wait(timeout=10)
        except subprocess.TimeoutExpired:
            row["attach_wait_timed_out"] = True
            # Stop may have timed out while its daemon request continued. Force
            # termination through the daemon, then bound the CLI and attach waits.
            docker(base, ["kill", name])
            attach_code = attach.wait(timeout=5)
        row["attach_exit_code"] = attach_code
        state = json.loads(docker(base, ["inspect", "--format", "{{json .State}}", name]))
        row["container_state_after_attach"] = state
        reader.join(timeout=3)
        if reader.is_alive():
            reader_errors.append("reader thread did not join within 3 seconds")
        row["output_bytes_seen"] = totals["seen"]
        row["retained_bytes"] = len(retained)
        row["retained_sha256"] = hashlib.sha256(retained).hexdigest()
        row["truncated"] = totals["seen"] > len(retained)
        row["retained_limit_respected"] = len(retained) <= RETAIN_LIMIT
        row["duration_seconds"] = time.monotonic() - started
    except Exception as exc:
        failure = repr(exc)
    finally:
        release.set()
        for process, field in ((stop, "stop_client_cleanup_error"),
                               (attach, "attach_client_cleanup_error")):
            try:
                kill_client(process)
            except Exception as exc:
                row[field] = repr(exc)
        if attach is not None:
            for stream in (attach.stdout, attach.stderr):
                if stream:
                    stream.close()
        if reader is not None:
            reader.join(timeout=3)
            if reader.is_alive():
                row["reader_join_failed"] = True
        if owned:
            try:
                # Resolve only containers bearing this newly generated run label.
                ids = docker(base, ["ps", "-aq", "--no-trunc", "--filter", f"label={label}"]).decode().split()
                row["cleanup_container_ids"] = ids
                row["job_cgroups_before_cleanup"] = {
                    cid: [str(p) for p in cgroups_for(cid)] for cid in ids
                }
                if ids:
                    docker(base, ["rm", "--force", *ids])
                row["cleanup_remove_succeeded"] = True
            except Exception as exc:
                row["cleanup_error"] = repr(exc)
            try:
                cleanup_ids = row.get("cleanup_container_ids", [])
                row["remaining_job_cgroups"] = {
                    cid: [str(p) for p in cgroups_for(cid)] for cid in cleanup_ids
                }
                cid = row.get("container_id")
                if cid and cid not in cleanup_ids:
                    row["remaining_job_cgroups"][cid] = [str(p) for p in cgroups_for(cid)]
                row["probe_cgroup_after_cleanup"] = cgroup_current_state(probe_cgroup)
                remaining = docker(base, ["ps", "-aq", "--no-trunc", "--filter", f"label={label}"]).decode().strip()
                row["remaining_run_containers"] = remaining.splitlines() if remaining else []
                cgroup_after = row["probe_cgroup_after_cleanup"]
                cgroup_remains = cgroup_after.get("observable") and cgroup_after.get("exists") and cgroup_after.get("procs")
                if (any(row["remaining_job_cgroups"].values()) or row["remaining_run_containers"]
                        or cgroup_remains):
                    row["cleanup_error"] = "investigation container or job cgroup remains"
            except Exception as exc:
                row["cleanup_verification_error"] = repr(exc)
    row["reader_errors"] = reader_errors
    if failure:
        row["error"] = failure
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=pathlib.Path)
    parser.add_argument("--image", required=True, help="exact image ID to diagnose")
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--rootfs-sha256", required=True)
    parser.add_argument("--probe-sha256", required=True)
    args = parser.parse_args()
    parts = args.output.resolve().parts
    if any(parts[index:index + 2] == ("docs", "evidence")
           for index in range(max(0, len(parts) - 1))):
        raise SystemExit("refusing to write diagnostic output under docs/evidence")
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    run_id = uuid.uuid4().hex[:12]
    report = {"kind": "issue-1 diagnostic; not an M0 campaign",
              "qualified": False, "m0_campaign": False, "run_id": run_id,
              "image_requested": args.image, "rootfs_sha256": args.rootfs_sha256,
              "probe_sha256": args.probe_sha256, "cases": [],
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "command": [sys.executable, *sys.argv],
              "host": socket.gethostname(), "platform": platform.platform(),
              "python": sys.version, "runner_sha256": hashlib.sha256(
                  pathlib.Path(__file__).read_bytes()).hexdigest()}
    error = None
    try:
        profile = json.loads(args.profile.read_text())
        profile_sha256 = hashlib.sha256(args.profile.read_bytes()).hexdigest()
        if profile_sha256 != EXPECTED_PROFILE_SHA256:
            raise RuntimeError("profile SHA-256 differs from immutable m0-004 manifest")
        if args.rootfs_sha256 != EXPECTED_ROOTFS_SHA256:
            raise RuntimeError("rootfs SHA-256 differs from immutable m0-004 manifest")
        if args.probe_sha256 != EXPECTED_PROBE_SHA256:
            raise RuntimeError("probe binary SHA-256 differs from m0-004 build record")
        if profile and isinstance(profile[0], dict):
            template = next(item["argv"] for item in profile if item.get("tag") == "create"
                            and item["argv"][-1] == "output")
        else:
            template = next(argv for argv in profile if "create" in argv
                            and len(argv) >= 2 and argv[-1] == "output")
        base = template[:3]
        required_pairs = (("--pull", "never"), ("--network", "none"),
                          ("--user", "65532:65532"), ("--cap-drop", "ALL"),
                          ("--security-opt", "no-new-privileges=true"),
                          ("--cgroupns", "private"), ("--ipc", "private"),
                          ("--pids-limit", "64"), ("--cpus", "0.5"),
                          ("--memory", "256m"), ("--memory-swap", "256m"),
                          ("--shm-size", "8m"), ("--restart", "no"),
                          ("--log-driver", "none"), ("--workdir", "/workspace"),
                          ("--entrypoint", "/probe"))
        if base != ["docker", "--host", "unix:///run/user/1000/docker.sock"]:
            raise RuntimeError("profile does not target the recorded rootless Docker socket")
        for flag, value in required_pairs:
            if flag not in template or template[template.index(flag) + 1] != value:
                raise RuntimeError(f"profile lacks required setting {flag} {value}")
        for flag, value in (("--ulimit", "nofile=256:256"),
                            ("--ulimit", "core=0:0"),
                            ("--tmpfs", "/workspace:rw,nosuid,nodev,size=64m,mode=0700,uid=65532,gid=65532"),
                            ("--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777")):
            pairs = [(template[i], template[i + 1]) for i in range(len(template) - 1)
                     if template[i] in ("--ulimit", "--tmpfs")]
            if (flag, value) not in pairs:
                raise RuntimeError(f"profile lacks required setting {flag} {value}")
        for flag in ("--volume", "-v", "--mount", "--env", "-e", "--privileged"):
            if flag in template:
                raise RuntimeError(f"profile contains disallowed setting {flag}")
        if "--read-only" not in template or not template[-2].startswith("sha256:"):
            raise RuntimeError("profile is not read-only or lacks the expected image position")
        if template[-2] != EXPECTED_PROFILE_IMAGE:
            raise RuntimeError("profile image ID differs from immutable m0-004 evidence")
        report["profile_path"] = str(args.profile)
        report["profile_sha256"] = profile_sha256
        report["profile_image_id"] = template[-2]
        report["runtime"] = json.loads(docker(base, ["version", "--format", "{{json .}}"]))
        image_inspect = json.loads(docker(base, ["image", "inspect", args.image]))[0]
        report["image_id_observed"] = image_inspect["Id"]
        if report["image_id_observed"] != args.image:
            raise RuntimeError("--image must be a content-addressed image ID matching Docker inspect")
        for mode in ("paused", "concurrent"):
            row = run_case(base, template, args.image, run_id, mode)
            report["cases"].append(row)
            report["docker_commands"] = COMMAND_LOG.copy()
            # Atomically replace only this new, run-specific report after each case.
            temp = args.output / ".result.tmp"
            temp.write_text(json.dumps(report, indent=2) + "\n")
            os.replace(temp, args.output / "result.json")
            if (any(key in row for key in ("error", "cleanup_error", "cleanup_verification_error",
                                           "reader_join_failed", "attach_client_cleanup_error",
                                           "stop_client_cleanup_error")) or row.get("reader_errors")):
                raise RuntimeError(f"case {mode} was incomplete; see recorded case observations")
    except Exception as exc:
        error = repr(exc)
        report["error"] = error
    report["diagnostic_interpretation"] = (
        "Compare stop timing and process/output/cleanup observations only. "
        "This diagnostic cannot qualify a runtime or change m0-004."
    )
    report["docker_commands"] = COMMAND_LOG.copy()
    report["exit_status"] = 1 if error else 0
    temp = args.output / ".result.tmp"
    temp.write_text(json.dumps(report, indent=2) + "\n")
    os.replace(temp, args.output / "result.json")
    print(json.dumps(report, indent=2))
    if error:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
