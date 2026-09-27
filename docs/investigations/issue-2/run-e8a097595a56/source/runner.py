#!/usr/bin/env python3
"""Bounded Issue #2 Docker-backed output-flood regression; never an M0 qualification run."""

import argparse
import hashlib
import json
import os
import pathlib
import platform
import socket
import behavior
import subprocess
import time

from behavior import (OUTPUT_LIMIT, STOP_DEADLINE_SECONDS, drain_attached)

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


def observe_cgroup(path, cid):
    """Bind a live scope observation to the full container ID, not a PID namespace."""
    root = pathlib.Path('/sys/fs/cgroup').resolve(strict=True)
    path = pathlib.Path(path).resolve(strict=True)
    if not path.is_relative_to(root) or path.name != f'docker-{cid}.scope':
        raise RuntimeError('cgroup path is not the target container scope')
    procs_text = (path / 'cgroup.procs').read_text()
    events_text = (path / 'cgroup.events').read_text()
    try:
        events = dict(line.split() for line in events_text.splitlines())
    except ValueError as exc:
        raise RuntimeError(f'malformed cgroup.events: {events_text!r}') from exc
    if events.get('populated') not in ('0', '1'):
        raise RuntimeError(f'missing or invalid populated field: {events_text!r}')
    # populated includes descendants; direct cgroup.procs can legitimately be empty.
    # https://www.kernel.org/doc/html/v6.9/admin-guide/cgroup-v2.html
    return {'host_path': str(path), 'cgroup_procs': procs_text.split(),
            'cgroup_procs_raw': procs_text, 'cgroup_events_raw': events_text,
            'observed_live': events['populated'] == '1'}


def cgroup_current_state(snapshot):
    if not snapshot or snapshot.get('observed_live') is not True:
        return {'observable': False, 'error': 'no live target scope observation'}
    path = pathlib.Path(snapshot['host_path'])
    try:
        root = pathlib.Path('/sys/fs/cgroup').resolve(strict=True)
        if not path.resolve().is_relative_to(root):
            raise RuntimeError('recorded cgroup path escaped cgroup root')
        try:
            path.stat()
        except FileNotFoundError:
            return {'observable': True, 'exists': False}
        return {'observable': True, 'exists': True,
                'procs': (path / 'cgroup.procs').read_text().split()}
    except (OSError, RuntimeError) as exc:
        return {'observable': False, 'error': repr(exc)}


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
    commands = []
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    total = {"seen": 0}
    probe_cgroup = None
    diagnostics = {}
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

        def record_cgroup(path):
            nonlocal probe_cgroup
            observation = observe_cgroup(path, cid)
            row['cgroup_observation_attempts'] = row.get('cgroup_observation_attempts', 0) + 1
            row['cgroup_last_observation'] = observation
            row['cgroup_observed_after_output_bytes'] = total['seen']
            if observation['observed_live']:
                probe_cgroup = observation
                row['probe_cgroup_live'] = observation
                return True
            return False

        outcome, code = drain_attached(
            base + ['start', '--attach', name], 'output', started, base, name, cid,
            captured, total, commands, diagnostics=diagnostics, on_cgroup=record_cgroup)
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

    except Exception as exc:
        row['error'] = repr(exc)
        row['passed'] = False
    finally:
        row['diagnostics'] = diagnostics
        # Text encoding is explicit; bounded raw stream bytes are preserved in main().
        row['output_bytes_seen'] = total['seen']
        row['retained_bytes'] = sum(map(len, captured.values()))
        row['truncated'] = total['seen'] > row['retained_bytes']
        row['docker_commands'] = commands
        row['captured_hex'] = {key: bytes(value).hex() for key, value in captured.items()}
        row['cleanup_verified'] = False
        if owned:
            try:
                ids = docker(base, ['ps', '-aq', '--no-trunc', '--filter', f'label={label}']).decode().split()
                # The known target remains cleanup-owned even if label discovery fails to list it.
                cid = row.get('container_id')
                if cid and cid not in ids:
                    ids.append(cid)
                row['cleanup_container_ids'] = ids
                if ids:
                    docker(base, ['rm', '--force', *ids])
                row['cleanup_remove_succeeded'] = True
            except Exception as exc:
                row['cleanup_error'] = repr(exc)
                # Discovery failure must not prevent a bounded attempt on the known target.
                if row.get('container_id'):
                    try:
                        docker(base, ['rm', '--force', row['container_id']])
                    except Exception as cleanup_exc:
                        row['target_cleanup_error'] = repr(cleanup_exc)
            try:
                after = cgroup_current_state(probe_cgroup)
                row['probe_cgroup_after_cleanup'] = after
                remaining = docker(base, ['ps', '-aq', '--no-trunc', '--filter', f'label={label}']).decode().split()
                row['remaining_run_containers'] = remaining
                row['cleanup_verified'] = (
                    row.get('cleanup_remove_succeeded') is True
                    and 'cleanup_error' not in row
                    and probe_cgroup is not None and probe_cgroup.get('observed_live') is True
                    and not remaining and after.get('observable') is True
                    and after.get('exists') is False)
                if not row['cleanup_verified']:
                    row['cleanup_verification_error'] = 'cleanup absent or unobservable; cannot pass'
            except Exception as exc:
                row['cleanup_verification_error'] = repr(exc)

    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=pathlib.Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--rootfs-sha256", required=True)
    parser.add_argument("--probe-sha256", required=True)
    args = parser.parse_args()

    args.output.mkdir(mode=0o700, exist_ok=False)
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
        "host_observed": socket.gethostname(),
        "uid_observed": os.getuid(),
        "platform_observed": platform.platform(),
        "python_observed": platform.python_version(),
        "runner_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "behavior_sha256": hashlib.sha256(pathlib.Path(behavior.__file__).read_bytes()).hexdigest(),
    }

    if args.rootfs_sha256 != EXPECTED_ROOTFS_SHA256:
        raise SystemExit(f"rootfs sha256 mismatch: {args.rootfs_sha256}")
    if args.probe_sha256 != EXPECTED_PROBE_SHA256:
        raise SystemExit(f"probe sha256 mismatch: {args.probe_sha256}")

    profile_bytes = args.profile.read_bytes()
    profile_sha256 = hashlib.sha256(profile_bytes).hexdigest()
    report["profile_sha256"] = profile_sha256
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
    for stream, data in row.pop('captured_hex').items():
        (args.output / ('output.' + stream)).write_bytes(bytes.fromhex(data))
    report["status"] = "PASS" if row.get("passed") and row.get("cleanup_verified") else "INCONCLUSIVE"
    report["docker_commands"] = COMMAND_LOG.copy()

    (args.output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
