# Current handoff

## State

M0 runtime **UNQUALIFIED**. M1 **NOT STARTED**. Qualification is paused.
This handoff accompanies the initial public foundation commit. At preparation
there was no prior commit. Resolve its exact SHA without a self-referential edit:
`git log --reverse --format='%H %s' | head -1`. Expected published branch: main,
remote: git@github.com:admbahm/DryDock.git. Expected tree after publication: clean,
with only ignored local IDE/build/cache artifacts. Verify Git/remote state on entry.

Last completed work in this snapshot: publication review; byte-preserving PRD
move under docs; public docs/agent guidance and issues #1–#5 created/verified; local checks passed. No
harness repair, remote-host operation, new campaign or M1 work during housekeeping.

## Problem and evidence

m0-004's output-flood stop command exceeded ten seconds; initial forced cleanup
also timed out. Later checks found no campaign containers or job cgroups; probe
images were removed. Approved rootless daemon was left running. This is last
observed state, not a current host health assertion.

Hypothesis: synchronous stop blocks the runner while output is no longer drained.
Root cause remains unestablished; this is not a proven Docker isolation failure.
Flood output retention and other qualification coverage remain incomplete.

All specimens are immutable and INCONCLUSIVE. Manifest SHA-256 references:

- m0-001: a91e3fbd138056330c93d65e685c0835609a45f75226b13c1b4e54bf37ad2581
- m0-002: fe968feb2cb80233125c3380f1295b3a8358609603e0f6f4f6011e3bb04bc9d8
- m0-003: a2e4ffff4dbfc760ce0ac12c0ba008568f1b38498f932cf280451e80697e34c6
- m0-004: a0f26ecf5aaf7ba38c5e56d6abf12af17ea32d2be17f9d5f9f85bb0831521a89

Read `docs/evidence/m0-004/README.md`, `behavior/result.json`, and the live
`tools/m0probe/behavior.py` before drawing conclusions. Snapshots are evidence,
not an edit target.

## Exact next action

After the operator resumes engineering, address GitHub issue #1: make a local,
deterministic subprocess/pipe reproduction of output production plus synchronous
termination, collect timelines/output/cleanup evidence, and establish or reject
the backpressure hypothesis. Then implement/test the smallest supported repair
and #2 regression coverage. Only then consider separately authorized #3 runtime
qualification with a new identity. Issues #4 and #5 remain deferred/blocked.

Do not rerun existing campaign scripts (hard-coded m0-004 names), modify specimen
bytes/hashes, weaken the ten-second or output limits, inspect real secrets, use
sudo/passwords, start M1/providers/TUI, or push without new explicit authorization.
Do not change GitHub ownership, integrations or administration. No standing
publication authority follows from the initial housekeeping push.

## Resume checks and unresolved decisions

```sh
git status --short --ignored
git log -1 --format='%H %s'
git remote -v
git ls-remote origin refs/heads/main
go test ./...
go vet ./...
python3 -m unittest discover -s tools/m0probe -p 'test_*.py'
```

Verify each evidence manifest from its directory (`shasum -a 256 -c manifest.sha256`)
and compare its digest above. See development.md for formatting/cross-build checks.
Do not format evidence source. Existing checks do not prove full harness correctness.

Unresolved: root cause and repair; remaining runtime coverage; exact eventually
qualified configuration; explicit M1 authorization; future module-path migration;
provider-related M0 choices intentionally deferred. GitHub Issues own actionable
work; no duplicate TODO file. Before a context/usage stop, replace this operational
state with verified current facts, commit reference, blocker and next action.
Never record credentials or secrets.
