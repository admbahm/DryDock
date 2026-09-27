# Architecture and trust boundaries

This is the approved direction, not a claim of implemented task execution.
Implemented today: CLI prerequisite reporting and experimental M0 probe tooling.

```text
CLI (later TUI)
    -> versioned owner-restricted local API
    -> controller + durable SQLite queue/state
    -> leased, bounded worker helper process
    -> frozen candidate patch
    -> independent inspector in fresh isolated execution
    -> controller-owned evidence bundle
    -> AWAITING_REVIEW
    -> explicit human decision on the unchanged bundle
```

One deployable headless service owns contracts, state transitions, leases,
authorization and events. One active task initially. Clients do not own execution
lifetime. Worker messages and repository instructions cannot alter authority.

The execution broker enforces tool/path/network/resource policy. A worktree alone
is not isolation. Workers and checks receive no host credentials, controller
storage, arbitrary mounts or runtime socket. The broker, not the worker, operates
the runtime. Required budgets must be enforceable before dispatch.

The inspector uses pinned checks and protected assets against a fresh candidate
materialized from the pinned base. Worker-authored checks only supplement required
checks. Missing, timed-out or interrupted evidence cannot pass. Evidence artifacts
are independently collected, attributable and bound to contract, base, candidate,
profile and manifest digests. Human acceptance cannot be inferred from test exit
codes and never pushes or merges code.

The future controller adapter may contact an authorized inference endpoint.
Reactor is the future Ollama endpoint, not the assumed controller or execution
host. `drydock-exec` is the current Linux qualification host only. Runtime support
must be qualified independently for the actual image/profile/configuration.

Go and SQLite through database/sql are approved. CLI-first; no TUI yet. Stable
worker boundaries should support later providers without changing authorization
or inspection. Routing, retries, live models and escalation are not implemented.
See the PRD and decisions for milestone scope. M1 needs explicit authorization.
