# Implementation evidence

## Increment 1: foundations and prerequisite reporting

Implemented: Go module, minimal CLI, bounded Docker metadata query, fail-closed
preflight report, and approved architectural decisions. No task execution exists.

Observed development environment: Darwin 27.0.0 arm64, Go 1.24.5, no Docker
executable in PATH. This is not the supported Linux execution environment.

Tests cover unsupported-host rejection before Docker access, unavailable or
malformed metadata, rootful and rootless metadata, misleading rootless labels,
metadata output bounds, CLI JSON/exit behavior, and unsupported commands.

Verification performed on the development host:

- `go test ./...`: passed for cmd/drydock and internal/sandbox.
- `go vet ./...`: passed.
- Native CLI build: passed.
- Linux/amd64 cross-build: passed; binary was not executed on Linux.
- Native `drydock preflight`: exited 1 and emitted `qualified: false` with
  `linux_host` as the blocker.

Builds/tests used `GOCACHE=/tmp/drydock-go-cache` to keep cache writes within
the available workspace permissions.

Unproven: every behavioral isolation requirement; Linux runtime execution;
contract validation; SQLite durability; worker protocol; independent inspection;
evidence binding; cancellation and recovery. No PRD acceptance criterion is
claimed satisfied by this increment.

Next dependency: operator selection/access to an independently qualified Linux
execution host. Reactor's future inference role does not select that host.

## Increment 2: M0 campaign 001

The operator selected `drydock-exec` as the dedicated Linux execution host,
separate from Reactor. Host specifications remain operator-reported.

Campaign result: **INCONCLUSIVE**, stopped at host access. SSH name resolution
failed with exit code 255 both inside and outside the local network sandbox.
No remote commands ran; no packages, configuration, or runtime resources were
created. No cleanup was necessary. Runtime isolation remains unobserved; this
is not a rootless Docker failure or pass. No M1 work was begun.

Preserved specimen: [M0 campaign 001](evidence/m0-001/README.md).
Manifest: [manifest.sha256](evidence/m0-001/manifest.sha256).
Manifest SHA-256: `a91e3fbd138056330c93d65e685c0835609a45f75226b13c1b4e54bf37ad2581`.

The specimen includes the read-only reproduction command and both observed
failures, without SSH configuration, keys, credentials, or host secret contents.
Next required input: a resolvable address or explicit SSH route from this
workspace. A later campaign will preserve this specimen unchanged.

## Increment 3: M0 campaign 002

Campaign result: **INCONCLUSIVE** at installation privilege access. SSH to the
operator-supplied IP succeeded outside the local network sandbox. Observed:
`drydock-exec`, Ubuntu 24.04.5 LTS, kernel 6.8.0-142-generic, x86_64, user adam
(UID 1000). `sudo -n true` exited 1: a password was required. No remote
installation/configuration changes or isolation probes followed. No campaign
resources required cleanup. M1 remains untouched.

Specimen: [M0 campaign 002](evidence/m0-002/README.md).
Manifest: [manifest.sha256](evidence/m0-002/manifest.sha256).
Manifest SHA-256: `fe968feb2cb80233125c3380f1295b3a8358609603e0f6f4f6011e3bb04bc9d8`.

Campaign 001's manifest and all listed file hashes were reverified unchanged.
Campaign 002 preserves the prerequisite command and observed outputs without
credential material. Required next step: operator-provisioned noninteractive
installation access or operator-performed privileged setup. No password sharing.

## Increment 4: M0 campaign 003

Result: **INCONCLUSIVE**, stopped at rootless setup prerequisite. SSH confirmed
Docker packages 5:29.8.1-1~ubuntu.24.04~noble and containerd.io
2.3.6-1~ubuntu.24.04~noble, system runtime units masked/inactive, and lingering
enabled. The rootless setup check exited 1 requesting `modprobe nf_tables`.
No bypass, sudo operation, daemon configuration, or container execution followed.
No campaign resources needed cleanup. No M1 implementation occurred.

Specimen: [M0 campaign 003](evidence/m0-003/README.md).
Manifest: [manifest.sha256](evidence/m0-003/manifest.sha256).
Manifest SHA-256: `a2e4ffff4dbfc760ce0ac12c0ba008568f1b38498f932cf280451e80697e34c6`.

The setup diagnostic is not an independently verified kernel-module state.
All behavioral isolation properties remain unproven. Required next step is
operator review/manual remediation of the prerequisite, followed by a new run.

## Increment 5: M0 campaign 004

Final result: **INCONCLUSIVE**. Unprivileged rootless setup succeeded. Docker
29.8.1 / containerd 2.3.6 / runc 1.5.1 / RootlessKit 3.1.0 ran on the observed
Linux 6.8.0-142-generic host. Configuration inventory and several bounded
resource/synthetic isolation probes recorded passes, with scope limits described
in the specimen. No overall acceptance criterion or runtime qualification passes.

The output-flood probe's stop operation exceeded its ten-second deadline; initial
forced removal also timed out. Qualification stopped. Synchronous stop while
attached output is not drained is a plausible harness defect, not a proven
Docker defect. Flood output retention was incomplete. Remaining recovery,
fail-closed and other coverage were not run. No M1 code was implemented.

Subsequent checks found no campaign containers or Docker job cgroups. Campaign
images were removed after archiving. The approved rootless service remains
running; synthetic host evidence/tooling is retained. No sudo was executed.

Specimen: [M0 campaign 004](evidence/m0-004/README.md).
Manifest: [manifest.sha256](evidence/m0-004/manifest.sha256).
Manifest SHA-256: `a0f26ecf5aaf7ba38c5e56d6abf12af17ea32d2be17f9d5f9f85bb0831521a89`.

The specimen preserves exact image archives, source snapshots, profiles, runtime
versions and observations. Local Go tests/vet and the static Linux probe build
passed; three Python evaluator tests passed. These do not prove full harness
correctness. Earlier campaign specimens remain immutable. The next step is to
repair/test qualification output handling before a separately identified run.

## Public repository foundation

Runtime work paused for public repository housekeeping. No harness repair, new
campaign or M1 implementation is part of this increment. Publication review
found no credential material in candidates; ordinary reproducibility metadata
was deliberately retained. See [publication review](publication-review.md).
The authoritative PRD moved byte-for-byte to docs/DryDock_PRD_v0.1.1.docx.
All four historical manifests and artifacts remain unchanged.

README, agent guidance, architecture, development/bootstrap notes and evidence
interpretation now provide durable project context. [HANDOFF.md](HANDOFF.md) is
the canonical immediate continuation record. Actionable work lives in GitHub
Issues; no competing TODO file or milestone objects are introduced. The next
engineering action remains a harness-level investigation, not a runtime rerun.

Created backlog: [#1 harness investigation](https://github.com/admbahm/DryDock/issues/1),
[#2 output-flood regressions](https://github.com/admbahm/DryDock/issues/2),
[#3 qualification rerun/completion](https://github.com/admbahm/DryDock/issues/3),
[#4 gated M1 slice](https://github.com/admbahm/DryDock/issues/4), and
[#5 deferred Reactor integration](https://github.com/admbahm/DryDock/issues/5).
Used existing bug label; added milestone:m0, milestone:m1, milestone:m2,
area:harness, area:runtime and blocked. No administrative settings changed.

Local checks passed: gofmt on live sources; go test ./...; go vet ./...; three
Python evaluator tests; native CLI build; static Linux/amd64 probe cross-build;
Linux-targeted probe vet. Evidence/artifact hashes and archived input tar hashes
were reverified. These checks do not establish runtime qualification.

## Issue #1: output/stop backpressure investigation and harness repair

Two corrected diagnostic-only Docker A/B runs used the same imported synthetic
probe image, archived profile, rootless Docker/runtime versions, and bounded
output handling. In each run, the paused-drain case left `docker stop` pending
for the unchanged ten-second deadline; releasing the output drain when stop
started returned stop in 0.063 s and 0.076 s. The third run also observed a
one-second `docker inspect` timeout while stop was pending. After drain resumed,
the container state became observable as exited. Both modes retained at most
1 MiB, recorded truncation, and found no run-labelled container or probe cgroup
after cleanup. Reports and exact commands are preserved in
`investigations/issue-1/README.md` and the run JSON files; neither run was a
qualification campaign.

Established: the live M0 harness synchronously waits for Docker stop at the
output threshold without draining attached stdout/stderr. Repeating the A/B
comparison with only drain resumption changed reproduces the timeout versus
sub-0.08-second split. This establishes a harness-level coupling between the
blocked attach stream and termination/control completion. It does not establish
the Docker daemon's internal mechanism or an isolation failure. m0-004 remains
INCONCLUSIVE and immutable; M0 remains UNQUALIFIED.

Fixed locally in `tools/m0probe/behavior.py`: start the existing `docker stop
--time 2` request asynchronously, continue draining both streams, retain no
more than 1 MiB combined, record truncation, and enforce the same ten-second
stop deadline. Added a deterministic local output-flood test with a child and
grandchild; it verifies both are live before cancellation, the stop operation
overlaps continued output, retention stays capped, truncation is reported, and
both processes are reaped.
Verification: `gofmt -l` reported no unformatted Go source; `go test ./...`,
`go vet ./...`, native CLI build, Linux/amd64 probe cross-build, Linux-targeted
vet, Python compilation, all 5 Python tests, and `git diff --check` passed. Go
checks used `/private/tmp/drydock-issue1-go-cache` because the default cache was
outside the write sandbox. All four historical evidence manifests verified.
These local checks do not exercise Docker cleanup or prove runtime qualification.
Issue #2's real container/job-cgroup regression acceptance remains open.

No M0 qualification campaign or M1 implementation was run. Full Go/Python and
evidence-integrity checks are complete. Final diff review and commit
`2867b40` (`fix: prevent output backpressure during probe termination`) are
complete. Branch `fix/1-output-backpressure` was pushed and verified at
`1c56111a04b014ea151fed153a8f64cf2f224f2c`. PR [#6](https://github.com/admbahm/DryDock/pull/6)
was merged into `main` after independent review.

## Issue #2: output-flood cancellation regressions — review correction

PR #7 was opened at `0270c4e` against `e2115d6`. Independent review found
blocking gaps in stop-process-group coverage, exception cleanup/diagnostic
retention, and Docker cgroup cleanup verification. The original completion
claim was too strong; Issue #2 remains open.

The original run `e11f05eb2c0c` and its JSON hash remain unchanged. It supports
bounded output and stop completion, but full cleanup is INCONCLUSIVE because
the runner accepted unobservable cgroups. Remote transfer/file/image cleanup
claims lack supporting command records in the preserved artifact. See the
[attributed correction](investigations/issue-2/REVIEW-CORRECTION.md).

Local repairs share the production drain/attach path, protect client cleanup on
exceptions, persist bounded failure diagnostics, require positive cgroup
observability, and test a real stop descendant before fallback cleanup. These
changes have no new Docker execution evidence. A separately authorized bounded
regression with a new identity is still needed; Issue #3 is not included.

Historical specimens remain immutable. m0-004 is INCONCLUSIVE; M0 is UNQUALIFIED;
M1 is NOT STARTED. No qualification campaign or M1 work occurred.

### Authorized bounded rerun: 86a56976e3cf

Result INCONCLUSIVE before output consumption: target scope was found but live
membership validation failed. No bounded-stop result is claimed. Exact source,
transfer/hash checks, runtime observations, image verification and cleanup records
are in [the run record](investigations/issue-2/run-86a56976e3cf/README.md).
The container, exact scope, imported image and temporary files were subsequently
verified absent. No retry or qualification campaign followed. The cause of the
membership observation remains unknown; startup timing is only a hypothesis.

### Authorized bounded rerun: e8a097595a56

PASS for this regression only: 8 MiB read, 1 MiB retained, truncation true, stop
exit zero in 0.118 seconds. The target scope was positively observed populated
with PID 11977, then explicitly absent after cleanup; no run-labelled containers
remained. Transfer checks, input/image verification and image/file/result cleanup
are preserved in [the run record](investigations/issue-2/run-e8a097595a56/README.md).
Exact executed sources match the local repaired runner/helper. This does not
retroactively change 86a56976e3cf, qualify M0 or authorize Issue #3/M1. Changes
remain uncommitted/unpushed, pending human review and publication authorization.

### Authorized publication of the review fixes

The owner authorized committing and pushing the repaired sources, local tests,
correction records and both new bounded-run records to the existing Issue #2
branch/PR #7. The four pre-existing Issue #1 investigation artifacts are excluded.
Human review and any merge remain separate; no issue closure or qualification
claim is authorized. Verify PR head against the resulting commit when resuming.
