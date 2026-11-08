# Roadmap and backlog recommendation

Planning record dated 2026-11-08, not a second issue tracker. GitHub Issues remain
the actionable backlog. No issue, milestone or remote setting was changed by this
review. [The orchestration proposal](orchestration-proposal.md) requires owner
approval and does not authorize implementation. Preserve the PRD M0–M4 order.

## Observed baseline and existing dependencies

Reviewed local commit `11207542494ba52f31149ce4f93a9cb917eedda7`, live CLI/preflight
source, M0 harness/tests, PRD, project guidance and GitHub issues #1–#5 plus PRs
#6/#7. GitHub reported both PRs merged and issues #1/#2 closed on this review date.
Those workflow states do not qualify a runtime. The implementation has prerequisite
reporting and experimental probes, no task execution, SQLite dependency, scheduler,
provider adapter or TUI. Approved designs are not implemented features.

| Order | Existing backlog / PRD milestone | Evidence and authorization before advancing |
| --- | --- | --- |
| 1 (closed) | [#1 harness investigation](https://github.com/admbahm/DryDock/issues/1), [PR #6](https://github.com/admbahm/DryDock/pull/6) | Recorded backpressure diagnosis/repair; historical m0-004 remains INCONCLUSIVE |
| 2 (closed) | [#2 cancellation regressions](https://github.com/admbahm/DryDock/issues/2), [PR #7](https://github.com/admbahm/DryDock/pull/7) | Local tests and bounded run e8a097595a56 support this regression only; prior inconclusive runs remain preserved |
| 3 (open, gated) | [#3 complete runtime qualification](https://github.com/admbahm/DryDock/issues/3), M0 | Explicit campaign authorization; new identity; all required runtime observations, stop on FAIL/INCONCLUSIVE, cleanup and manifest. Provider-related M0 work stays explicitly deferred; runtime qualification alone is not full M0 completion |
| 4 (open, blocked) | [#4 fake-worker vertical slice](https://github.com/admbahm/DryDock/issues/4), M1 | #3 runtime proof plus explicit M1 authorization; contract/storage/state, bounded fake, independent inspection, evidence, cancellation/recovery. No live models or TUI |
| 5 (open, deferred) | [#5 Reactor adapter](https://github.com/admbahm/DryDock/issues/5), M2 | M1 completion and explicit M2 authorization; resolve deferred connectivity/model/data-policy prerequisites; AC02 fixture evidence and bounded failure |
| 6 (no issue yet) | PRD M3 frontier escalation | M2, approved adapter/data scope and enforceable spend bounds; AC03/AC05/AC06; identical inspection |
| 7 (no issue yet) | PRD M4 review/release proof | M3; TUI/CLI parity, digest-bound acceptance and all AC01–AC12 evidence. Release proof does not authorize publication |

Recommendation: retain #3 -> #4 -> #5. Seek authorization for #3 only when the
owner intends a new campaign; do not repeat closed diagnostics solely for planning.
After owner approval to write backlog, create narrowly scoped M3/M4 issues from
the existing PRD, followed by proposal review and the increments below. No new
issue is needed merely to duplicate this document. The former handoff's pending
PR #7 publication instruction is obsolete; local main includes its merge commit.

## Proposed increments after the v0.1 proof

These labels are proposal identifiers, not approved milestones or promised dates.
Each requires owner approval of the amendment and its implementation scope. Keep
new interfaces internal until exercised; add no empty packages or plugin system.

| Increment | Dependencies and smallest useful slice | Independent exit evidence |
| --- | --- | --- |
| P1 durable graph, serial dispatch | M4 and approved amendment; operator-supplied bounded DAG, fake workers, one execution at a time | Reject cycles/missing inputs; duplicate events and restart at every dispatch boundary cannot duplicate results or paid calls; failed prerequisite blocks dependents; explicit resume after cleanup |
| P2 deterministic integration | P1; artifact ownership, frozen lineage and stable integration order | Replay identical inputs to the same candidate digest; conflicts block; stale input invalidates descendants; individually passing patches that fail aggregate regression cannot reach review |
| P3 bounded parallel dispatch | P2; ready-node concurrency on one independently qualified execution host | Independent nodes overlap, dependent nodes wait; workspace isolation and aggregate resource/spend reservations hold under contention; cancellation prevents dispatch and reaps all trees within ten seconds; restart cannot accept late leases |
| P4 capability and escalation scheduling | P3 and proven M2/M3 adapters; deterministic eligibility policy | Capability/context/privacy/unavailability tests choose only eligible workers; denied disclosure makes zero external calls; concurrent reservations cannot overspend; retries stay within objective limits; same verification for each tier |
| P5 bounded objective decomposition | P4; planner proposes graph within owner-authorized envelope | Adversarial plans cannot expand scope, checks or budgets; ambiguous goals block; graph revision invalidates stale evidence; compare proposed plan with frozen authorized graph |
| P6 document workflow | P5 plus approved document artifact schema; extraction/preparation first, synthesis optional | Pinned documents yield validated structured outputs with source provenance; malicious embedded instructions grant no authority; missing citations/truncation are visible; unauthorized frontier synthesis makes zero external calls |

Build observability into each increment, starting with P1 IDs/events and adding
parallel resource accounting in P3 and provider attribution in P4. Before claiming
frontier savings, publish a reproducible comparison methodology for owner review
and measure the same workload under the declared baseline. No savings claim or
model suitability conclusion is established by this planning task.

The conservative sequence intentionally earns concurrency with fake workers and
integration tests before autonomous decomposition. Changing this order requires
an explicit proposal, not reinterpretation of M1. Distributed scheduling, cross-
repository objectives, plugin loading and deployment expansion remain deferred.
