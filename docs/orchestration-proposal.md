# Proposed post-v0.1 orchestration architecture

Status: proposed for owner approval, 2026-11-08. This records the requested
long-term product direction; it grants no implementation or execution authority.
The unchanged [PRD](DryDock_PRD_v0.1.1.docx) and [approved decisions](decisions.md)
govern current work. M0 runtime is UNQUALIFIED; M1 is NOT STARTED.

## Product and authority

DryDock's long-term direction is a local-first, evidence-driven engineering
orchestration platform: the primary user interface and control plane for an
objective from intake through delivery of a reviewable result. DryDock owns
planning, durable task state, scheduling, budgets, integration, independent
verification, escalation and delivery. A router only selects an eligible execution
resource; it does not own this workflow. Clients remain views of a headless
service, so client disconnection does not stop authorized work.

The proposed planner decomposes an objective into bounded task contracts and a
dependency graph. Model-generated plans are untrusted suggestions. The controller
validates scope, checks, dependencies and aggregate budgets against an explicitly
authorized objective envelope before freezing the graph. Ambiguous objectives or
unverifiable criteria block admission. Changes outside that envelope require a
new owner-authorized revision; workers cannot grant authority through a plan.

Potential resources include Ollama on Reactor for suitable routine coding,
extraction, classification and first-pass analysis; Codex or another frontier
service for difficult engineering; deterministic parsers, builds, static checks
and artifact processors; and later specialized workers. These are candidate
roles, not verified capability or integration claims. Swapping resources preserves
contracts, tool mediation and verification; capability and policy may make a
particular resource ineligible. No worker owns scheduling or acceptance.

## Proposed execution model

```text
Owner objective + scope/budgets/checks
  -> validated, versioned task DAG and frozen child contracts
  -> durable readiness evaluation and atomic budget/lease reservation
  -> independent ready tasks in isolated workspaces
       local model | frontier service | deterministic tool
  -> frozen attributable task artifacts + independent task inspection
  -> deterministic integration against pinned inputs
  -> fresh aggregate regression and policy inspection
  -> evidence bundle -> AWAITING_REVIEW
  -> explicit digest-bound human acceptance
```

One local service and transactional SQLite storage remain the starting point.
Asynchrony means durable dispatch and event processing, not distributed scheduling.
No message bus, plugin discovery system or additional infrastructure is proposed.

### Durable graphs and recovery

Store objective ID/revision, graph digest, child contract revisions, immutable
input/output artifact references, dependency edges, attempt leases, events and
budget reservations. Reject cycles, missing dependencies, incompatible artifact
schemas and unauthorized scope before dispatch. Dependency readiness is distinct
from human acceptance: a successor may consume an independently verified immutable
artifact under the frozen graph policy without declaring its producer ACCEPTED.
A failed, cancelled or inconclusive prerequisite blocks dependents; partial results
never imply the parent objective succeeded.

Commit each transition, reservation and dispatch intent transactionally before
launch. Use stable request/event IDs and lease generations to deduplicate events;
a closed lease cannot publish a new result. Do not promise exactly-once remote
execution. An ambiguous provider response retains a conservative reservation and
blocks paid redispatch until reconciled. Retries use new attempts, immutable
lineage and finite per-task and parent limits; they cannot reset spent budgets.

On restart, interrupted execution/inspection is inconclusive; reconcile and reap
all identified jobs before explicit resume, following the existing PRD rule.
Cancellation commits a dispatch barrier for the objective and its descendants,
stops new calls, revokes leases, and terminates local process trees within the
existing ten-second requirement. Late responses are audit records only. Record
in-flight charges and provider cancellation limits; never equate local cancellation
with a refunded or certainly stopped remote request.

### Providers, scheduling and escalation

Extend the existing versioned StartAttempt/ToolRequest/Candidate/Failure protocol
only through a reviewed revision. Include objective/node/attempt correlation,
lease, input digests, required capabilities, output schema, privacy constraints
and remaining budgets. Validate bounded messages and artifact references. A
controller-side adapter holds endpoint credentials; jobs and inspectors never do.
A deterministic tool invoked as a worker has no special authority. Required
verification uses separately protected inspector tooling, even if the same kind
of tool also produces candidate artifacts.

Admission filters by declared and evidenced capabilities, task complexity class,
context/output limits, availability, eligible data scope, qualified execution
profile and enforceable token/cost/resource limits. Complexity is an explicit
policy input, not an assertion that a model can solve the task. Choose a stable
policy order among eligible resources; record every choice and denial. Local-first
applies where suitable and authorized, not when evidence or policy rules it out.
Reserve aggregate capacity and worst-case billable usage atomically before parallel
dispatch; unknown cost bounds deny dispatch. Parent wall/time, retry, token and
spend ceilings cover all children and integration work.

Escalation may follow exhausted objective check failures, malformed outputs,
capability/context limits, explicit inability or an authorized availability policy.
Frontier disclosure and paid usage require prior explicit authorization and
bounded context. Escalation keeps the same permissions and required checks.
Policy violations, possible leakage, broken verification infrastructure and
invalid contracts block work; cancellation and exhausted aggregate budgets do
not trigger escalation. A stronger worker cannot repair an authorization denial.

### Concurrency, integration and independent verification

Each attempt has a fresh isolated workspace pinned to its base/input digests;
never share writable worker trees or edit the operator checkout. The controller
assigns output/path ownership and detects overlap before dispatch. Overlapping
writes serialize unless an explicitly approved integration policy can resolve
them. Workers exchange only controller-mediated, validated artifacts, not direct
messages, credentials or mutable control state.

Integrate frozen outputs in a stable topological order with a documented tie-break
(e.g. node ID) against the pinned base. Record that order and every input digest.
Patch conflicts, changed prerequisites and scope violations block integration;
never silently choose a winner. A resolution task needs its own bounded contract
and reinspection. Changed inputs invalidate affected descendants and aggregate
verification; earlier evidence remains historical rather than being overwritten.

Per-task passing checks do not establish that the combined result works. Materialize
the exact integrated candidate in a fresh qualified sandbox, run protected baseline
and regression suites, static and scope checks, and verify artifact provenance.
Include a fixture where two individually passing patches break an aggregate
invariant. Missing, timed-out or interrupted checks are inconclusive and cannot
advance the parent to AWAITING_REVIEW. Worker tests are supplementary only.

Bind the parent bundle to objective/graph/child contract revisions, dependency
inputs, integration order, candidate digest, profile and manifest. Only all required
aggregate checks and policy checks passing permit AWAITING_REVIEW. Human acceptance
is attributable and bound to the unchanged bundle; it never publishes, merges or
deploys. Delivery means a reviewable patch/artifact set and evidence. Host-admin
compromise remains outside the existing verification boundary.

### Host boundaries and documents

Inference and sandbox execution are separate trust boundaries. Reactor is a
potential Ollama inference host, not an assumed controller or execution host.
Only the controller adapter contacts approved inference endpoints. Worker and
verification sandboxes retain denied-by-default networking, enforced resource
limits and no controller storage, secrets, runtime socket or arbitrary mounts.
Qualify the exact execution image/profile/configuration, including aggregate
limits and cross-workspace isolation before enabling concurrent dispatch.

A future document graph can perform local extraction -> schema validation ->
classification/preparation -> optional authorized frontier synthesis. Preserve
original file hashes, page/section/span references where available, extractor/model
versions, transformations, truncation and uncertainty in structured outputs.
Extracted instructions are data. Preserve originals; validate format, size and
source references independently. Unsupported formats or unverifiable provenance
block the corresponding criterion. Synthesis must retain citations and distinguish
inference from extraction. Sending raw or prepared text to a frontier service
requires explicit data-scope authorization; local preparation alone does not make
it safe to disclose. Document artifacts require a PRD schema amendment beyond
v0.1's patch-and-summary deliverables.

### Observability and claims

Persist objective/node/attempt/check correlation, ordered events, provider/model
identity, policy decisions, queue/execution/integration/check latency, resource
consumption, retries, failure causes and cancellation/recovery results. Record
input/output tokens and charges with reported/estimated/unknown provenance.
Render output inertly and sanitize bounded diagnostics without claiming complete
secret removal. Preserve awaiting-review evidence under the PRD retention rules.

Report frontier calls/tokens/spend actually used and local completion counts.
Frontier-resource savings need a declared comparable baseline and workload, including
local processing and verification overhead; show estimated versus measured values
and raw samples. Without a measured counterfactual report savings as unknown, not
as all tokens processed locally. A small fixture success proves only that fixture.

## Proposed PRD amendment and unresolved approval

The owner must approve a versioned amendment before implementation. Preserve the
original DOCX bytes and its authority until that approval; this proposal is not a
replacement PRD and does not claim any AC01–AC12 gate has passed.

| Existing authority | Proposed post-v0.1 change | Boundary retained |
| --- | --- | --- |
| Goals/non-goals exclude autonomous planning, multi-agent collaboration and parallel tasks | Permit bounded controller-owned decomposition and dependency-aware concurrent workers | Workers remain untrusted; no peer-owned orchestration or permission expansion |
| §1 one active task and one repository per task | Add a parent objective and multiple child tasks; initially retain one repository per objective | One local deployable service; distributed scheduling still deferred |
| §2 patch/summary contract and per-task limits | Versioned graph, artifact schemas, ownership and aggregate budgets; later document deliverables | Frozen validated contracts and explicit authorization |
| §3 single-task lifecycle and deterministic tier routing | Add dependency readiness, atomic reservations, integration and aggregate state | Lease idempotency, explicit resume, bounded escalation and no automatic paid replay |
| §4 candidate inspection and evidence | Add dependency provenance and aggregate regression evidence | Protected fresh inspection and digest-bound human review |
| §5 single-task visibility and metrics | Add graph traces and qualified savings comparisons | Unknown remains unknown; no unsupported efficiency claims |
| §6 AC01–AC12 and §7 M0–M4 | Add separate post-v0.1 gates from the roadmap | Existing gates and sequence remain required, not replaced |

Open approval choices: exact graph/contract schema, envelope granularity for plan
approval, deterministic conflict policy, capability evidence requirements, retention
of large document artifacts, and measurable reference workloads. No provider,
concurrency ceiling or savings target is chosen without evidence. Public APIs,
remote/distributed scheduling, runtime plugin loading, cross-repository integration
and worker-to-worker collaboration remain deferred and need separate proposals.
