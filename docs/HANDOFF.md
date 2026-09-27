# Current handoff

## State and authority

M0 runtime **UNQUALIFIED**; M1 **NOT STARTED**. Do not run m0-005, Issue #3, or
any qualification campaign. The owner authorized local fixes and then a new bounded Issue #2 Docker
regression. The owner subsequently authorized committing and pushing these
fixes/evidence to update PR #7. Merge remains unauthorized. After an initial automatic-review transfer block, the owner explicitly approved
the four exact payloads/destination. The first bounded attempt completed INCONCLUSIVE. After local readiness repairs,
the owner explicitly authorized another attempt, e8a097595a56, which passed. Both
attempts are closed and all scoped remote resources/files have been cleaned up.

Branch: `test/2-output-cancellation-regressions`. Before this publication, remote head was
`0270c4e493eb6f9aaae029a09272f577473e4d23`; base/main is
`e2115d6b8dd6e953d94d1631641671bfccdaf64f`. PR #7 exists:
https://github.com/admbahm/DryDock/pull/7
This handoff accompanies the fix/evidence commit following that head. Resolve
`git log -1` and compare origin/PR head when resuming; do not infer publication
from this file alone.

## Local changes

- Shared production attach/drain helper owns client cleanup from launch through
  selector setup, observation and exception paths. The Docker runner imports it.
- Failure output and partial diagnostic state are retained. Stop/default limits
  remain ten seconds and 1 MiB combined. Case deadline remains 42 seconds.
- Stop-process-group test establishes a live descendant and checks its death
  before fallback cleanup. Production worker-cleanup tests do the same for a
  synthetic parent and child on case timeout and non-zero stop failure.
- Cgroup evidence must identify a live full-ID scope and explicitly observe that
  same scope absent after cleanup. Unobservable/permission failures, remaining
  empty scopes and removal errors cannot pass. The runner records source hashes.
- Corrected the production caller's string/Path mismatch without running it
  against Docker. Removed copied drain code and misleading failure tests.
- Added `docs/investigations/issue-2/REVIEW-CORRECTION.md`. Original run JSON is
  unchanged. Its cleanup evidence remains INCONCLUSIVE; the new successful
  run is recorded below. Issue #2 remains open for review.

## Evidence and limits

The original report `regression-run-e11f05eb2c0c.json` remains at SHA-256
`fe3b2f03d34304f5eebebb16cdebcf0e4e588708e2f70c0d787aad8932c8fc9c`.
Its PASS is the original runner's classification, not independent acceptance.
See the correction for cgroup, transfer and cleanup evidence gaps. Run `86a56976e3cf` executed once, with verified inputs/image, and stopped
INCONCLUSIVE: target cgroup scope found but membership validation failed before
any output was consumed or stop issued. The exact cause is unknown; raw membership
values were not retained. Startup timing is only a hypothesis. The target
container, exact scope, imported image and temporary files were subsequently
verified absent. Sources, report, operation log and hashes are preserved under
`docs/investigations/issue-2/run-86a56976e3cf/`. That identity was not reused;
a subsequent separately authorized run is recorded below.
Historical m0-001 through m0-004 remain immutable, and
m0-004 remains INCONCLUSIVE. Source changes do not retroactively repair evidence.

## Checks and next action

19 local Python tests passed after the local readiness follow-up. The in-memory leader-only termination mutation
was rejected by the new descendant test. Python compilation, Go tests/vet, native
build, Linux probe cross-build/vet, formatting, diff checks and all four historical
manifest verifications passed. Cross-builds do not prove Linux execution. The Linux-specific test subreaper path is unexecuted on macOS.

Publication is authorized for this branch and these fixes/evidence only.
The second explicitly authorized rerun e8a097595a56 passed. Record:
`docs/investigations/issue-2/run-e8a097595a56/README.md`.
It observed 8 MiB read, 1 MiB retained/truncated, stop exit zero in 0.118 seconds,
live populated target scope/PID 11977, exact scope absence after cleanup and no
run containers. Transfer hashes and image/file/result cleanup are preserved.
Result SHA-256: e5c671e7be0c48bc220cf3186eaacb0e1eafe948fd99ef2bdadca5488b781067.
The completed first run remains INCONCLUSIVE. No remote cleanup is outstanding.
Next: verify the authorized push updates PR #7 to the fix/evidence commit,
then perform human review. Do not merge or close issues on the owner's behalf. Human merge remains separate. No further runtime run is needed
for this request or authorized implicitly by this result.

Expected tree after publication: tracked changes committed, with only the four
pre-existing investigation artifacts below left untracked. Preserve the four pre-existing provenance-unverified files:
`docs/investigations/issue-1/independent-local-pipe.json`, `local-pipe.json`,
`local-pipe.py`, and `tools/m0probe/reproduce_backpressure.py`. Do not stage them.
The original Issue #1 transfer incident remains recorded in its investigation
README and is not resolved by these changes.
