# Current handoff

## State

Current milestone: M0. Runtime **UNQUALIFIED**; M1 **NOT STARTED**. Do not run
m0-005, begin M1, or start another qualification campaign. The current branch is
`fix/1-output-backpressure`, based on published `main` at
`fe26751691fe502c33b22ebd864296ade542dc38`. There is no Issue #1 commit yet.
The working tree contains a local harness repair, tests, and investigation
records; inspect `git status` before continuing.

## Last completed action

Reproduced the output/stop behavior in two corrected bounded Docker A/B
diagnostics, established the harness-level root cause, and implemented the
smallest corresponding live-tool fix in `tools/m0probe/behavior.py`. Added a
deterministic local child/grandchild output-flood regression. Current focused
Python suite: 5 tests pass. `go test ./...`, `go vet ./...`, native CLI build,
Linux/amd64 probe cross-build, Linux-targeted vet, Python compilation, and all
four historical evidence manifests also pass. Go checks used
`/private/tmp/drydock-issue1-go-cache` because the default cache was outside the
write sandbox. Investigation details, commands, report hashes, and limits are
in `docs/investigations/issue-1/README.md`.

Corrected diagnostic reports:

- Run 02, `7bc8cac7bcce`, report SHA-256
  `041289005e629519a8e0d10bdc13ef5b3afce3a82fc8ba963b1ceebb2cc71f4e`.
- Run 03, `1d57f990b4db`, report SHA-256
  `30c70d070d73ce3d02647eb3b20402afee5a59044262a8bdc021076399d6de43`.
- Run 03 runner SHA-256
  `ea825a72f80904012ea396b7120d3a9398a58c826063e51d205201dc544839c0`.

Both diagnostics are not qualification campaigns and do not qualify any
runtime. Run 03 found no run-labelled containers or probe cgroups after cleanup.
The local regression test does not create Docker resources, so actual
container/job-cgroup regression coverage remains unresolved and Issue #2 must
remain open unless separately satisfied.

## Established facts and uncertainty

Across corrected Docker runs, the same profile/image/runtime had stop time out
at the ten-second deadline with output draining paused, while concurrent output
draining allowed stop to return in under 0.08 seconds. The paused run's separate
inspect request also timed out at its one-second bound; after output draining
resumed, the container state was observable and exited. This establishes the
harness-level cause: synchronous stop waiting while attached output is not
drained couples control completion to a blocked attach stream. The internal
Docker daemon mechanism remains unknown. This is not evidence of an isolation
failure. The fix now starts stop asynchronously while the same selector keeps
draining both streams. Retention remains 1 MiB combined, truncation is recorded,
and the stop deadline remains ten seconds.

Historical evidence remains immutable. m0-004 stays **INCONCLUSIVE**; M0 stays
**UNQUALIFIED**. No new qualification campaign was run. Issue #3 remains
separate.

On session resumption, the checkout was already on
`fix/1-output-backpressure`; three untracked artifacts existed but were absent
from the committed handoff: `tools/m0probe/reproduce_backpressure.py`,
`docs/investigations/issue-1/local-pipe.py`, and
`docs/investigations/issue-1/local-pipe.json`. Their provenance is
pre-existing/unverified. They were inspected as requested, preserved, and their
existing JSON was not accepted as evidence. An additional untracked
`independent-local-pipe.json` was also found without provenance in the committed
handoff; it remains untrusted and preserved. A separate local-pipe experiment
was independently run; it demonstrates local OS-pipe backpressure only.

The remote-transfer exception is permanent: `scp -p` mistakenly targeted
`adam@192.168.50.99:/tmp/` with generic filenames rather than checked unique
destinations. Whether those three paths had earlier contents cannot now be
resolved; do not infer they were empty. The current transferred files were
removed only after exact hash checks and operator authorization, and those exact
paths were verified absent. On the latest resumption check they remained absent;
no cleanup was attempted then. This incident is not evidence about Docker.
Complete chronology is preserved in the investigation README.

## Exact next actions

1. Review `git diff` and `git status`, and stage only the justified Issue #1
   repair, tests, verified diagnostic records, and documentation. Keep the
   pre-existing provenance-unverified files preserved but unstaged.
2. Issue #2 remains open: its real Docker-backed regression must still verify
   output-flooding child/grandchild cleanup and no residual campaign
   container/job cgroup under the repaired harness. Do not turn that work into a
   qualification campaign.
3. Recheck staged changes and historical evidence manifests, commit the
   coherent Issue #1 fix, push only `fix/1-output-backpressure`, and open a PR
   against `main` as authorized. Do not merge or approve it.

Do not use `tools/m0probe/reproduce_backpressure.py` unchanged, change the
ten-second deadline or 1 MiB output cap, run m0-005, start M1, use credentials,
modify historical evidence, or push to `main`. The initial wrong generic `/tmp`
transfer must never be represented as though its unique-name precheck succeeded.

## Resume checks

```sh
git status --short --branch
git log -1 --format='%H %s'
git remote -v
python3 -m unittest discover -s tools/m0probe -p 'test_*.py'
go test ./...
go vet ./...
```

The expected eventual branch push is authorized only for the Issue #1
development branch. Do not change GitHub administration or merge the PR.
