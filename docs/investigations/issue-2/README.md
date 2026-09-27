# Issue #2 Investigation & Regression Evidence

## Overview

GitHub Issue #2: "Add deterministic output-flood cancellation regression coverage"
Milestone: M0 (Runtime UNQUALIFIED; m0-004 INCONCLUSIVE; M1 NOT STARTED).

Following the harness-level fix for output backpressure during probe termination (PR #6, Issue #1), Issue #2 provides deterministic regression coverage across both local synthetic execution and an authorized, bounded Docker-backed regression on `drydock-exec` (192.168.50.99).

This work is **not** an M0 qualification campaign, does not run `m0-005`, does not begin M1, and does not qualify any runtime.

---

## Local Deterministic Regression Coverage

Local tests were added to `tools/m0probe/test_behavior.py` exercising the repaired `drain_until_complete` control flow in isolation:

1. **Happy path concurrent drain during stop**:
   - `test_output_flood_is_drained_during_bounded_stop_and_reaps_tree`: Verifies child and grandchild output flooding (4 MiB total) is drained while stop is in flight, stop completes in < 10s, output retention caps at 1 MiB, truncation is recorded, and the full process tree is reaped.
2. **Stderr-only flooding**:
   - `test_stderr_only_flood_triggers_output_limit_and_caps_retention`: Verifies stderr output alone crosses the 1 MiB threshold, triggers bounded stop, caps retained stderr at 1 MiB (with 0 bytes retained on stdout), records truncation, and reaps the worker process tree.
3. **Stop non-zero exit / failure**:
   - `test_stop_nonzero_failure_raises_runtime_error_and_reaps`: Verifies that a stop process exiting with code 42 immediately raises `RuntimeError('Docker stop exited 42')`, prevents any success verdict, and cleanly reaps the worker process tree.
4. **Stop timeout & process group kill**:
   - `test_stop_timeout_kills_stop_proc_and_raises_timeout_expired`: Verifies that a stop process that hangs beyond the stop deadline is terminated via `SIGKILL` to its process group, raises `subprocess.TimeoutExpired`, and reaps the worker process tree.
   - Tested using an injectable `stop_deadline=0.3s` parameter while preserving the production default of `STOP_DEADLINE_SECONDS = 10`.
5. **Case deadline expiration**:
   - `test_case_deadline_exceeded_raises_timeout_error_and_reaps`: Verifies overall case timeout raises `TimeoutError` and reaps the process tree.

All 9 Python tests in `tools/m0probe/` pass (`Ran 9 tests in 3.4s`).

---

## Docker-Backed Regression on `drydock-exec`

### Execution Parameters & Safeguards

- **Target Host**: `drydock-exec` (192.168.50.99), Ubuntu 24.04.5 LTS, kernel 6.8.0-142-generic, user `adam` (UID 1000).
- **Runtime**: Rootless Docker 29.8.1, containerd 2.3.6, runc 1.5.1, RootlessKit 3.1.0, slirp4netns 1.2.1.
- **Privilege**: Unprivileged user execution only. No `sudo` requested, used, or authorized.
- **Synthetic Assets**:
  - Profile: `docs/evidence/m0-004/behavior/commands.json` (SHA-256 `34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1`)
  - Rootfs: `docs/evidence/m0-004/behavior-rootfs.tar.gz` (SHA-256 `b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1`)
  - Probe Binary: `/probe` (SHA-256 `7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f`)
- **Run Identity**: `e11f05eb2c0c`
- **Unique Remote Filenames** (prechecked absent before transfer):
  - Runner: `/tmp/drydock-issue2-e11f05eb2c0c-runner.py` (SHA-256 `451360c3d3cbf61d2ef2c706dbbeb86fa8959443b3b91d4a26381f36d7279fcd`)
  - Profile: `/tmp/drydock-issue2-e11f05eb2c0c-profile.json` (SHA-256 `34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1`)
  - Rootfs: `/tmp/drydock-issue2-e11f05eb2c0c-rootfs.tar.gz` (SHA-256 `b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1`)
  - Output directory: `/tmp/drydock-issue2-e11f05eb2c0c-result/`
- **Imported Image**: `sha256:5352933279766818665a3da1d03550db8daf9c1f71e9ca96eec185cd2fae4cf6` (verified probe binary matches `7076129...`)
- **Container Name**: `drydock-issue2-e11f05eb2c0c-output`
- **Container Label**: `drydock.issue2.run=e11f05eb2c0c`

### Observations & Observations Record

Report file: `docs/investigations/issue-2/regression-run-e11f05eb2c0c.json` (SHA-256 `fe3b2f03d34304f5eebebb16cdebcf0e4e588708e2f70c0d787aad8932c8fc9c`).

- **Stop Duration**: `0.116s` (< 10s deadline).
- **Total Output Seen**: `8,388,608 bytes` (8 MiB).
- **Retained Bytes**: `1,048,576 bytes` (exactly 1 MiB cap respected).
- **Truncation**: `true`.
- **Exit Code**: `2` (probe normal exit on cancel).
- **State After Stop**: `Running: false`, `Status: exited`.
- **Termination Reason**: `output_limit`.
- **Stop Exit Code**: `0`.
- **Cgroup Path Observed Live**: `/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/user.slice/docker-79b03053e0115fdf2987f3f9e06de74f8121e712319b74dddb6dccaca35e6ce0.scope`.
- **Cleanup Verification**:
  - Container `79b03053e011...` removed via `docker rm --force`.
  - Filter `label=drydock.issue2.run=e11f05eb2c0c` returned 0 containers.
  - Job cgroup scope path confirmed absent.
  - Remote files verified via SHA-256 and removed.
  - Temporary result directory removed via `rmdir`.
  - Imported image removed via `docker rmi`.
  - Post-cleanup checks on remote host confirmed 0 containers, 0 images, and no cgroup remnants.
- **Regression Status**: **PASS**.

---

## Limitations

- This regression verifies output draining and bounded termination under the repaired harness for the synthetic output probe.
- It does not test multi-agent dispatch, production tasks, or distributed scheduling.
- It does not constitute an M0 qualification campaign or qualify the M0 runtime.
- M0 remains UNQUALIFIED; m0-004 remains INCONCLUSIVE; M1 remains NOT STARTED.
