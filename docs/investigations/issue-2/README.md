# Issue #2 regression evidence

Issue #2 remains **open for review**. Local repairs address the independent-review
findings at PR #7 head `0270c4e`. The latest authorized bounded regression,
[e8a097595a56](run-e8a097595a56/README.md), passed with positive live-scope and
post-cleanup absence evidence. The owner authorized committing and pushing the
fixes/evidence to PR #7 for review. This is not runtime qualification; merge is
not authorized.

Read the [attributed review correction](REVIEW-CORRECTION.md) for findings,
local repairs, preserved hashes and the exact evidence limits.

## Preserved run e11f05eb2c0c

The [original report](regression-run-e11f05eb2c0c.json) is unchanged. Its embedded
PASS value is the original runner's classification, not an accepted disposition.
It records 8 MiB read, 1 MiB retained, truncation, stop completion in about
0.116 seconds, container removal and an empty run-labelled container query.
The cgroup observation/absence checks do not establish complete cleanup reliably.

The original narrative's claims of destination prechecks, transfer verification,
remote file/result cleanup and image removal lack preserved command/output
records here. Treat them as unverified; do not silently convert them to facts.
The original narrative and runner remain available at commit `0270c4e`.

## Local verification and next boundary

`test_behavior.py` covers successful concurrent draining and stderr-only flooding.
`test_issue2_failures.py` exercises production attach cleanup, exception diagnostic
persistence, a stop-process descendant, and fail-closed cgroup observations.
These tests use local synthetic processes or mocks, never a Docker daemon.

The Docker runner now imports `behavior.py` rather than embedding a copy. Any
separately authorized execution must record and verify both transferred sources.
It requires a fresh output directory and must use a new run identity. The first new Docker attempt is recorded below; it did not establish the required
output-cancellation evidence. Do not close Issue #2
on local tests alone, or rerun a campaign without explicit authorization.

This work does not qualify a runtime. Historical m0-004 stays INCONCLUSIVE;
M0 stays UNQUALIFIED; M1 stays NOT STARTED. Issue #3 remains separate.

Local verification on macOS: 17 Python tests passed; an in-memory leader-only
termination mutation was rejected by the new descendant test. Python compilation,
Go tests/vet, native build, Linux probe cross-build/vet, formatting and diff checks
passed. All four historical manifests verified unchanged. The Linux-specific
subreaper test path was not executed on this macOS host.

## Authorized rerun 86a56976e3cf

The [new bounded run](run-86a56976e3cf/README.md) stopped INCONCLUSIVE when live
cgroup membership could not be established, before any output was read or stop
requested. Inputs and image were verified. Subsequent scoped checks established
container, exact cgroup, imported-image and temporary-file cleanup. The raw report
is preserved; no retry occurred. Issue #2 remains open and merge remains blocked.

The [local readiness follow-up](READINESS-FOLLOWUP.md) adds bounded pending-to-live
observation and raw cgroup diagnostics. Its 19 local tests pass; no remote
execution has verified that revision. The earlier run remains unchanged.

## Successful bounded rerun e8a097595a56

The [new record](run-e8a097595a56/README.md) preserves verified transfers, exact
source snapshots, raw results and scoped cleanup. It read 8 MiB, retained 1 MiB,
recorded truncation and completed stop in 0.118 seconds. It observed populated 1
and PID 11977 in the full-ID target scope, then verified the scope absent and no
run-labelled container remaining. Image and temporary-file removal are recorded.
This satisfies the missing bounded Docker observation for these sources; human
review remains necessary. Earlier inconclusive results retain their classifications.
