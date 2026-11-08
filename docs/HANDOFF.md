# Current handoff

## State and authority

As of the 2026-11-08 architecture review: M0 runtime **UNQUALIFIED**; M1 **NOT
STARTED**. This task authorizes documentation/planning only. No campaign, M1,
live-provider work, issue mutation, push, PR, merge or deployment is authorized.
The owner subsequently authorized committing and pushing this documentation
change on a dedicated branch. That permission does not authorize a PR or merge.
The unchanged PRD remains authoritative. The new orchestration amendment is
proposed for owner approval, not adopted requirements.

## Observed baseline and local changes

Local branch at review start: `main`, commit
`11207542494ba52f31149ce4f93a9cb917eedda7` (PR #7 merge). Read-only GitHub queries
confirmed PRs #6/#7 merged and issues #1/#2 closed; #3/#4/#5 remain open. The former
handoff’s instruction to finish publishing PR #7 is superseded by these observations.
Prior run details and corrections remain in progress and investigation records.

The reviewable local diff updates README, AGENTS, architecture, decisions, progress
and this handoff, and adds `docs/orchestration-proposal.md` and `docs/roadmap.md`.
It defines the future control plane, identifies PRD conflicts and recommends a
dependency-ordered backlog without changing GitHub. No runtime source or dependency
was edited. Publication branch: `codex/orchestration-architecture`. The owner authorized a
commit and push of these eight documentation files only. Resolve the resulting
commit with `git log -1`; verify its remote branch before claiming publication.

## Evidence and limits

The CLI still only reports prerequisites and always denies qualification; the
repository has experimental M0 tooling, no task execution or SQLite dependency.
Approved single-task designs are not implemented capabilities. Proposal details
and exit criteria have not been demonstrated by a runtime.

Historical m0-001 through m0-004 remain immutable and INCONCLUSIVE. The bounded
Issue #2 run e8a097595a56 passed its regression only; it does not qualify M0 or
authorize #3. The earlier 86a56976e3cf run remains INCONCLUSIVE. Corrections and
exact records are under `docs/investigations/issue-2/`; no new remote work occurred.
The original Issue #1 transfer incident remains recorded in its investigation
README and is not resolved by this planning work.

## Next action and expected tree

Owner review of the proposed amendment and roadmap is next. Any adoption must
explicitly revise authority; implementation is separately gated. The next current
runtime backlog item is #3, requiring explicit campaign authorization. Successful
runtime qualification alone neither completes deferred provider-related M0 work
nor authorizes M1. Do not act on old publication permissions as standing authority.

Expected tree after publication: documentation changes committed, with only these
four pre-existing,
provenance-unverified untracked files, preserved and not staged:
`docs/investigations/issue-1/independent-local-pipe.json`, `local-pipe.json`,
`local-pipe.py`, and `tools/m0probe/reproduce_backpressure.py`.

## Validation of this documentation change

Passed: Go tests/vet, 19 local Python unit tests, native CLI build, Linux/amd64
probe cross-build and Linux-targeted probe vet. Live-source gofmt inspection
reported no changes needed. Diff whitespace and local Markdown link checks passed.
All four historical evidence manifests verified before and after edits; a separate
SHA-256 inventory confirmed every historical specimen file unchanged. The PRD
remains at SHA-256 `a80aba5eabc20f8a1f41c0b5d42cc0e62eabe95bf9989adc6d99b9c2c7c326e7`.
These checks establish local build/test and document integrity only; no Docker
campaign, Linux runtime execution or proposed orchestration behavior was tested.
