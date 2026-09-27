# Issue #1 investigation

## Reconciliation on resumed session

At the start of this session the checkout was already on
`fix/1-output-backpressure`, at `fe26751691fe502c33b22ebd864296ade542dc38`,
which matches fetched `origin/main`. The branch had not yet advanced. The working
tree had three untracked investigation artifacts:

- `tools/m0probe/reproduce_backpressure.py`
- `docs/investigations/issue-1/local-pipe.py`
- `docs/investigations/issue-1/local-pipe.json`

The committed `docs/HANDOFF.md` did not mention these files. Their provenance is
therefore **pre-existing and unverified**. All are preserved byte-for-byte. The
existing JSON is not treated as evidence until independently reproduced.

## Existing artifacts: review only

`local-pipe.py` starts a Python child that writes 8 MiB to stdout, reads past a
1 MiB threshold, pauses reading, waits 250 ms, and then starts draining in a
thread. This can demonstrate a local pipe writer blocking while its pipe is not
read. It does not exercise Docker, stderr, the original selector loop, or Docker
stop. Its waits are bounded, but exceptions can leave the reader thread or child
uncleaned; it is unsuitable as a regression test unchanged.

`local-pipe.json` reports `wait_without_drain_timed_out: true` and eventual exit
code 0. No command, interpreter/platform version, capture procedure, or provenance
is recorded. Treat these values as unverified claims, not observations established
by this session.

`tools/m0probe/reproduce_backpressure.py` proposes two Docker cases with the
archived synthetic image/profile: a reader held at a 1 MiB gate while `docker stop`
runs, and a reader released concurrently with stop. It does not invoke the full
qualification runner and records `qualified: false`. Static safety concerns found:
container creation occurs before the cleanup `try`; fixed names can collide; the
stopper/attach subprocesses are not managed as process groups; exceptional
cleanup can fail before a durable report is written; container removal and cgroup
cleanup are observed but not robustly guaranteed; and the profile/image must be
checked against the recorded artifacts before execution. It is not safe to run
unchanged.

An additional untracked `independent-local-pipe.json` was also found among the
investigation files. Its provenance is not established in the committed
handoff. It is preserved but not accepted as evidence; the independently run
`verified-local-pipe.py` result below is the local-pipe observation used here.
Current hashes identify the preserved bytes only; they do not establish
provenance:

```text
tools/m0probe/reproduce_backpressure.py  b7ec91a1ad8523c0705155f58febd61d8df40f45f45347ace035cb7d33d3ba10
docs/investigations/issue-1/local-pipe.py  7e488a04b07cc18e8c5e17d563775dd42d861e4a2085d15e3ddfe14ff1a7019f
docs/investigations/issue-1/local-pipe.json  1600067f2ab55f67900c8e232f2630f1a9cb963bbc03a1275c321f255eeec3d6
docs/investigations/issue-1/independent-local-pipe.json  d572ae946ebb60008a89ba1247ef22affc68fd27ae9309302251a7013e022338
```

## Evidence collected in this session

See `verified-local-pipe.py` and its generated `verified-local-pipe.json`. The
command was:

```sh
python3 docs/investigations/issue-1/verified-local-pipe.py --result docs/investigations/issue-1/verified-local-pipe.json
```

The script SHA-256 is
`29d4e90f749f04ef3775c3eaea97365457ecb4086b5441be1169dc8c3d2c3ef9`; the result
SHA-256 is
`14e84fd6200a31b9cad08a55164d09541c34433c950998f43822c4a436df2862`.

It exited 0 on Bridge, macOS 27.0 arm64, Python 3.14.6. The finite child tried
to write 8,388,608 bytes. With the parent paused after 1,114,112 bytes had been
read, a 250 ms child wait timed out. After draining resumed, 7,274,496 more
bytes were read and the child exited 0. Retention was 1,048,576 bytes, the
limit was respected, and truncation was recorded. Runtime was about 0.287 s;
the child was reaped and the drain thread joined. This is an independent
reproduction of local OS-pipe backpressure only. It does **not** establish why
Docker stop exceeded its deadline in m0-004.

The Bridge host can connect to `drydock-exec`; a read-only check confirmed its
rootless daemon is Docker 29.8.1, but the exact archived image digest is absent,
consistent with the historical cleanup record. The archived rootfs tarball's
SHA-256 matches its immutable manifest, and its `/probe` binary matches the
recorded binary SHA-256. Importing this rootfs with Docker 29.8.1 produced
diagnostic image ID `sha256:ab6ed89e550770873c0655a7382448973efee2ed8ceedc13c6735e1f905f6016`,
different from the historical image ID
`sha256:c93dd948b465f2ba26fd1c9f37c540c310424dd07fb74459f50354bf3e6c76f8`.
Image configuration metadata therefore differs; these observations do not
qualify or revise m0-004. Before execution, a created-but-never-started
container was exported and its `/probe` SHA-256 matched
`7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f`; that
verification container was removed. The read-only SSH check exited 1
because `docker image inspect sha256:c93dd948b465f2ba26fd1c9f37c540c310424dd07fb74459f50354bf3e6c76f8`
reported `No such image`; `hostname`, `id`, and Docker server version returned
`drydock-exec`, uid 1000 (`adam`), and `29.8.1`.

The pre-existing `tools/m0probe/reproduce_backpressure.py` is preserved. Static
review found fixed container names, no process-group control for Docker clients,
cleanup/reporting gaps on exceptions, and no validation of the supplied image
against the archived binary/profile. It is unsuitable and has not been run. A
replacement diagnostic runner must use unique names, take cleanup ownership
before create, bound each subprocess and the total experiment, cap combined
retained output, continue draining after release, record truncation, and verify
container and job-cgroup cleanup. Run only the targeted Issue #1 comparison with
synthetic probe content. It is not M0-005 and must never report qualification.
Infer cause only from observed differences and the recorded m0-004 lifecycle.

`tools/m0probe/diagnose_issue1_backpressure.py` is a purpose-built diagnostic,
not a qualification runner. It validates the exact profile hash and recorded
image/rootfs/binary inputs, uses unique per-run container names/labels, bounds
Docker calls to ten seconds, pauses only at a synchronized output threshold,
drains concurrently in the concurrent case, retains at most 1 MiB combined,
records truncation, and inspects cleanup. It reports `qualified: false` and
`m0_campaign: false`.

### Preliminary Docker diagnostic run 01 (not root-cause evidence)

The first execution used runner SHA-256
`18712b999f21daa8496538c36f08f5c93599c800ef31619e725839533446df27`; the
complete JSON is `diagnostic-run-01-preliminary.json` (SHA-256
`fc82b955ed766b92543ff8d40defedd5996f6888bbd38fa4d6f0a328fc68996c`). Run ID
`aaab49ecbde2`, on `drydock-exec` (Ubuntu 24.04.5 amd64, Linux
6.8.0-142-generic, Python 3.12.3, rootless Docker 29.8.1, containerd 2.3.6,
runc 1.5.1, RootlessKit 3.1.0, slirp4netns 1.2.1). The command and every
Docker argv, exit code, duration and output byte count are in the JSON.

The remote runner command was:

```sh
timeout -s INT -k 15s 180s python3 /tmp/drydock-issue1-25e9bbb85adb-runner.py --profile /tmp/drydock-issue1-25e9bbb85adb-profile.json --image sha256:ab6ed89e550770873c0655a7382448973efee2ed8ceedc13c6735e1f905f6016 --output /tmp/drydock-issue1-25e9bbb85adb-result --rootfs-sha256 b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1 --probe-sha256 7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f
```

The SSH command returned exit status 0. That status means the diagnostic
completed and cleanup checks ran; it does not mean stop passed or the runtime
qualified.

Observed: paused mode exceeded the ten-second stop deadline (10.013 s); after
draining resumed, the container/attach process exited. Concurrent mode drained
all 8,388,608 output bytes and stop returned in 0.070 s. Both retained exactly
1,048,576 bytes and recorded truncation. The report found no run-labelled
containers after cleanup; its cgroup-at-stop search found no path.

Do not treat this run as root-cause evidence. Review found that the runner
appended a second `output` argument to an archived argv that already contained
the probe mode, and its pre-cleanup cgroup listing used Docker's abbreviated
IDs. The extra argument is ignored by the current output probe, but the runner
defect must be corrected and the comparison repeated before accepting its
result. The timing difference is a strong lead, not confirmation. This run's
JSON is preserved unchanged and is not a qualification result.

The corrected runner preserves the single archived probe mode, requests full
container IDs during cleanup inspection, and records the live process cgroup
path before and after cleanup. Corrected runs 02 and 03 repeat the A/B comparison
with independent run identities and full cgroup observations.

### Corrected Docker A/B runs 02 and 03

Both runs used the same synthetic archived `/probe` bytes and profile, imported
diagnostic image `sha256:ab6ed89e550770873c0655a7382448973efee2ed8ceedc13c6735e1f905f6016`,
and rootless Docker 29.8.1 on `drydock-exec` (Ubuntu 24.04.5 amd64, Linux
6.8.0-142-generic, Python 3.12.3, containerd 2.3.6, runc 1.5.1, RootlessKit
3.1.0, slirp4netns 1.2.1). Each report has the full runtime metadata, command
argv, per-command exit/duration/output counts, container state, cgroup snapshots,
and cleanup observations. Both were diagnostic-only (`qualified: false`,
`m0_campaign: false`) and ran under a 180-second outer timeout.

Run 02 used runner SHA-256
`712bbaac5feca2476fb4097235c9e47e49859ff482ef4a66d2d3390c4abfc8c7`, run ID
`7bc8cac7bcce`, and report
`diagnostic-run-02-corrected.json` (SHA-256
`041289005e629519a8e0d10bdc13ef5b3afce3a82fc8ba963b1ceebb2cc71f4e`). Its SSH
command exited 0. Paused draining left stop pending for 10.015 s; concurrent
draining returned in 0.063 s. The paused case observed 3,244,032 bytes and the
concurrent case all 8,388,608 bytes. Both retained 1,048,576 bytes and recorded
truncation. Each probe cgroup was observed live at the output threshold and
absent after cleanup; no run-labelled container remained.

Full remote command:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=5 adam@192.168.50.99 'timeout -s INT -k 15s 180s python3 /tmp/drydock-issue1-1ae2b13e3d0d-runner-corrected.py --profile /tmp/drydock-issue1-25e9bbb85adb-profile.json --image sha256:ab6ed89e550770873c0655a7382448973efee2ed8ceedc13c6735e1f905f6016 --output /tmp/drydock-issue1-1ae2b13e3d0d-result --rootfs-sha256 b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1 --probe-sha256 7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f'
```

Run 03 used runner SHA-256
`ea825a72f80904012ea396b7120d3a9398a58c826063e51d205201dc544839c0`, run ID
`1d57f990b4db`, and report `diagnostic-run-03-docker-ab.json` (SHA-256
`30c70d070d73ce3d02647eb3b20402afee5a59044262a8bdc021076399d6de43`). Its SSH
command exited 0. Paused draining again left stop pending for 10.016 s; a
separate `docker inspect` request also timed out at its one-second bound while
stop was pending. Once output draining resumed, inspection returned and showed
the container exited; its `FinishedAt` was about 0.12 s after `StartedAt`, well
before the stop CLI's ten-second timeout. Concurrent draining returned stop in
0.076 s and observed all 8,388,608 bytes. Both modes retained 1,048,576 bytes,
recorded truncation, observed a live process cgroup at threshold, then found the
cgroup absent and no run-labelled containers after cleanup.

Full remote command:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=5 adam@192.168.50.99 'timeout -s INT -k 15s 180s python3 /tmp/drydock-issue1-9c64b02832ce-runner.py --profile /tmp/drydock-issue1-25e9bbb85adb-profile.json --image sha256:ab6ed89e550770873c0655a7382448973efee2ed8ceedc13c6735e1f905f6016 --output /tmp/drydock-issue1-9c64b02832ce-result --rootfs-sha256 b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1 --probe-sha256 7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f'
```

After each report had a local SHA-256-matching copy, the remaining uniquely
named transferred rootfs/profile/runners/results were hash-checked and removed.
The run-03 runner/report were also hash-checked immediately before their exact
paths were removed. Exact result directories were empty and removed with
`rmdir`. The diagnostic image ID was confirmed to have no referencing
containers, then removed by its content ID. The exact run labels had no
remaining containers. This cleanup touched only investigation-specific names;
it did not inspect or modify other `/tmp` content. The earlier generic-path
transfer uncertainty remains unresolved as documented above.

The controlled A/B difference was whether the attached-output drain remained
paused after the stop request started. Across the two corrected runs, paused
draining reproduced the stop timeout and concurrent draining did not. This
establishes the harness-level cause: synchronously waiting for Docker stop while
not draining the attached output couples completion of the termination/control
path to a blocked attach stream. The m0-004 source contains this exact
synchronous wait at the output threshold. The observations do not establish the
internal Docker daemon mechanism and do not indicate an isolation failure.
Alternative explanations considered were probe/runtime image differences
(same image ID and probe hash), resource-profile changes (same archived profile
hash), and different Docker/runtime versions (same observed runtime in both
runs); those do not explain the repeated A/B timing split. Timing and scheduler
variation remain possible contributors to exact durations, but not to the
repeated ten-second versus sub-0.08-second outcome under the controlled drain
change.

The smallest harness repair is to start `docker stop --time 2` as a bounded
background process and continue draining both attached streams while polling
for completion. The stop deadline remains ten seconds and retained stdout/stderr
remains capped at 1 MiB combined with truncation recorded. A deterministic local
regression test now drives a child/grandchild output producer while a fake stop
waits for its output completion; it verifies both processes exist before
cancellation starts, drain progress during stop, output cap, truncation, stop
completion, and process reaping. The test does not create a
Docker container or cgroup. Thus the local regression verifies the harness
control flow; it does not qualify Docker or fully satisfy Issue #2's container
and job-cgroup regression intent.

## Remote transfer exception

Before the later uniquely named diagnostic transfer, `scp -p` was mistakenly
given `adam@192.168.50.99:/tmp/` rather than the prechecked unique filenames. It
may have overwritten pre-existing files named `/tmp/behavior-rootfs.tar.gz`,
`/tmp/diagnose_issue1_backpressure.py`, or `/tmp/commands.json`. A subsequent
read-only check found those paths contain files matching the intended synthetic
rootfs, runner, and profile hashes respectively, but prior contents cannot be
established or recovered from current evidence. At that point no Docker image
had been imported and no container/A/B probe had been run. The files were
removed only after the operator authorized hash-guarded deletion. Immediately
before deletion, all three SHA-256 values matched the expected values below;
after deletion, all three exact paths were verified absent. This cleanup does
not resolve whether those paths contained earlier files before the mistaken
transfer. Do not infer that they were previously empty. This is an agent transfer
error, not a Docker or M0 result. The cleanup command checked these exact hashes:

```text
/tmp/behavior-rootfs.tar.gz b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1
/tmp/diagnose_issue1_backpressure.py fc3bfe9cbe091498ce5b210b2ee9a4b7b60db718711e8668ea7abf9ee8041a1b
/tmp/commands.json 34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1
```

All three matched immediately before removal and the exact paths were absent in
the post-cleanup check. On resumption of this work, the same three exact paths
were checked and remained absent; no deletion was attempted in that session.
Only those paths were removed during the authorized cleanup; no other `/tmp`
content was inspected or changed. The later diagnostic transfer used these explicit
destinations, verified absent before transfer and hash-checked before use:

```text
/tmp/drydock-issue1-25e9bbb85adb-rootfs.tar.gz  b183f6b35e8a8655faa93a032633d47a9b3920a6425afcb661a1012e6e7cdea1
/tmp/drydock-issue1-25e9bbb85adb-runner.py  18712b999f21daa8496538c36f08f5c93599c800ef31619e725839533446df27
/tmp/drydock-issue1-25e9bbb85adb-profile.json  34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1
```

The later image import and preliminary Docker diagnostic occurred only after
these unique-name checks. Subsequent corrected work uses new runner/result
destinations and keeps each run's record separate.

Historical specimens `m0-001` through `m0-004` remain immutable. m0-004 remains
INCONCLUSIVE; runtime remains UNQUALIFIED; M1 remains NOT STARTED.
