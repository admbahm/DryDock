# Issue #2 independent-review correction — 2026-09-27

Attribution: Codex, following the owner's request to fix the blockers found in
independent review of PR #7 at `0270c4e493eb6f9aaae029a09272f577473e4d23`.
This is a new interpretation and repair record, not a replacement campaign.

## Preserved observation and limits

`regression-run-e11f05eb2c0c.json` remains byte-for-byte unchanged, SHA-256
`fe3b2f03d34304f5eebebb16cdebcf0e4e588708e2f70c0d787aad8932c8fc9c`.
The original runner is recoverable at that commit, with SHA-256
`451360c3d3cbf61d2ef2c706dbbeb86fa8959443b3b91d4a26381f36d7279fcd`.
The current runner has changed and must not be attributed to that execution.

The report records 8 MiB read, 1 MiB retained, truncation, stop exit zero in
0.11578376599936746 seconds, container removal, and an empty run-labelled
container query. Its runtime metadata includes RootlessKit and Docker 29.8.1.

The report's PASS classification is insufficient to close Issue #2. It records
`probe_pid: 0`, no live PID-based cgroup snapshot, and an unobservable direct
post-cleanup cgroup check. A full-ID scope path and empty subsequent glob results
were recorded, but the old runner conflated lookup errors with absence and
accepted unobservable cleanup. The supported disposition for the full Docker
cleanup criterion is **INCONCLUSIVE**, not independently verified PASS.

Destination prechecks, remote transfer hash verification, remote host/user
identity, temporary-file removal and imported-image removal were asserted in
the original narrative without corresponding command/output records in this
artifact. They remain independently unverified. Local artifact hashes do not
establish these remote operations. No absence of execution is inferred from
absence of records, and no records have been reconstructed as observations.

## Local repair

- The Docker regression imports the production attach/drain implementation.
- Attach ownership covers selector setup, observation, draining and exceptions;
  client groups are signalled, direct children reaped, and descriptors closed.
- Stop-timeout coverage establishes a live stop descendant and verifies its
  termination before fallback teardown. The production default stays ten seconds.
- Failure paths retain bounded output and partial diagnostic state.
- Cleanup requires an observed live full-ID scope and a successful explicit
  absence check of that same path. Missing observations, permission errors,
  residual empty scopes and removal failures cannot pass.
- A fresh output directory is required. Future authorized runs must transfer
  both the runner and its production `behavior.py` dependency with recorded hashes.

Local verification: 17 Python tests passed on macOS; the new descendant test
rejected an in-memory leader-only termination mutation. Python compilation, Go
tests/vet, native build, Linux probe cross-build/vet, formatting/diff checks and
all historical manifest checks passed. Linux subreaper execution remains untested.

Local tests are not Docker cleanup evidence. A new, uniquely identified bounded
Docker regression needs separate explicit authorization; no such run was made
while fixing these blockers. Issue #2 remains open pending that evidence and
human review. Do not overwrite the original JSON or reuse its identity.

m0-001 through m0-004 remain immutable. m0-004 stays INCONCLUSIVE, M0 stays
UNQUALIFIED, and M1 stays NOT STARTED. No Issue #3, m0-005 or qualification work
was executed or authorized by this repair.
