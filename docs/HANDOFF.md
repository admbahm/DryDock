# Current handoff

## State

Current milestone: M0. Runtime **UNQUALIFIED**; M1 **NOT STARTED**. Do not run
m0-005, begin M1, or start another qualification campaign. The current branch is
`test/2-output-cancellation-regressions`, based on published `main` at
`e2115d6b8dd6e953d94d1631641671bfccdaf64f` (incorporating merged PR #6).
The working tree has four provenance-unverified investigation artifacts
preserved and unstaged; inspect `git status` before continuing.

## Last completed action

Completed all Issue #2 requirements:
1. Local deterministic regressions in `tools/m0probe/test_behavior.py` covering:
   - Stderr-only flooding (capped at 1 MiB, truncated, reaped).
   - Stop non-zero exit (RuntimeError, fail closed, reaped).
   - Stop timeout (SIGKILL to stop process group at deadline, TimeoutExpired, reaped).
   - Case deadline expiration (TimeoutError, reaped).
2. Executed authorized, bounded Docker-backed regression on `drydock-exec` (192.168.50.99):
   - Run ID: `e11f05eb2c0c`. Result: **PASS**.
   - Verified output flood (8 MiB seen) drained concurrently during stop in 0.116s.
   - Retained output capped at 1 MiB; truncation recorded; exit code 2.
   - Verified live cgroup scope at threshold.
   - Verified complete cleanup: container removed, 0 run containers remain, cgroup
     absent, transferred files verified and removed, imported image removed.
   - Report recorded in `docs/investigations/issue-2/regression-run-e11f05eb2c0c.json`
     (SHA-256 `fe3b2f03d34304f5eebebb16cdebcf0e4e588708e2f70c0d787aad8932c8fc9c`).
3. Verification passed: 9 Python tests pass; Go tests, vet, native and cross builds pass;
   git diff check clean; all 4 historical evidence manifests verified.

## Established facts and uncertainty

Issue #2 acceptance criteria are fully demonstrated by observed evidence:
- Output draining cannot be blocked by stdout or stderr backpressure.
- Stop timeouts, non-zero failures, and case deadlines fail closed with full cleanup.
- Docker container and job-cgroup lifecycle are cleanly managed under the repaired harness.

Historical evidence specimens `m0-001` through `m0-004` remain immutable.
m0-004 remains **INCONCLUSIVE**; runtime remains **UNQUALIFIED**; M1 remains **NOT STARTED**.
No qualification campaign was run. Issue #3 (qualification rerun) remains separate and
requires explicit human authorization.

## Exact next actions

1. Review git diff and commit the Issue #2 work.
2. Push `test/2-output-cancellation-regressions`.
3. Open PR against `main` referencing `Closes #2`.
4. STOP. Do not merge the PR, run m0-005, or begin M1.

## Resume checks

```sh
git status --short --branch
git log -1 --format='%H %s'
git remote -v
python3 -m unittest discover -s tools/m0probe -p 'test_*.py'
go test ./...
go vet ./...
```
