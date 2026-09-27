# Approved M0/M1 decisions

Authority: `docs/DryDock_PRD_v0.1.1.docx`, supplied by the operator, SHA-256
`a80aba5eabc20f8a1f41c0b5d42cc0e62eabe95bf9989adc6d99b9c2c7c326e7`.
Its internal title says v0.1; the filename says v0.1.1. The supplied bytes are
the planning authority, with the operator's approved scope restrictions below.

- Go; standard library where practical; module path `drydock` until a canonical
  repository path is selected.
- SQLite through database/sql, using modernc.org/sqlite. Dependency installation
  and persistence implementation follow runtime qualification.
- One headless service, one active task, durable local queue, CLI over a versioned
  owner-restricted Unix socket. No TUI implementation yet.
- Linux execution host. Rootless Docker is a candidate requiring behavioral
  qualification; worktrees and container metadata do not establish isolation.
- Reactor is the future Ollama inference endpoint. It is not presumed to host
  the controller or execution sandbox. Qualify the execution host independently.
- A deterministic fake is a bounded helper process crossing the worker protocol
  and execution boundary. No live providers or external disclosure during M1.
- Defer router until multiple selectable workers exist. No empty packages.
- Frozen contracts; controller-owned state and evidence; protected verification
  profiles; independent fresh-candidate inspection; passing means AWAITING_REVIEW.
- No operator-checkout writes, automatic acceptance, push, merge or deployment.
- Finite enforceable execution budgets; unsupported isolation fails closed.
- M0 live inference/connectivity/provider selection work remains deferred by
  explicit operator instruction. Full M0 completion must not be claimed.

Implementation order: foundations, runtime qualification, contract/storage/state
machine, fake-worker inspection loop, evidence and failure/recovery demonstrations.
The first fixture will be a small Go timeout parser with a negative-value bug,
pinned protected checks, and known good and bad patches.

Planned package boundaries are api, contract, controller, worker, sandbox,
inspector, evidence and storage. Create each only when its responsibility is
implemented. Human acceptance recording remains deferred to M4.

Current gate: M0 runtime UNQUALIFIED; M1 NOT STARTED and requires renewed explicit
authorization. Public GitHub ownership/administration remains with admbahm.
