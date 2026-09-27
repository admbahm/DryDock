# DryDock

DryDock is a controlled environment for agentic workers.

The intended workflow starts with a bounded task contract executed by an
untrusted worker. Candidate changes are independently inspected. Objective
evidence determines whether a result can proceed to human review. Policy may
permit bounded escalation to a stronger model; consequential actions remain
human-authorized.

**Workers are untrusted. Evidence is trusted. Humans authorize consequential actions.**
Evidence supports observed behavior within a defined verification boundary, not
universal correctness. Passing inspection means `AWAITING_REVIEW`, not `ACCEPTED`.

## Current state

Early-stage, under active development. **M0 runtime is UNQUALIFIED; M1 is NOT
STARTED.** The repository contains a Go CLI prerequisite check and experimental
qualification tooling. It does not yet execute task contracts. SQLite persistence,
worker orchestration, independent task inspection, Ollama/frontier integration,
escalation and a TUI are planned, not operational.

All four qualification campaigns are INCONCLUSIVE. In m0-004, rootless Docker
operated and several bounded-resource/synthetic-isolation probes produced
positive evidence, but the output-flood stop command exceeded ten seconds.
Harness output backpressure is a hypothesis, not an established Docker isolation
failure. Cleanup found no campaign containers or job cgroups remaining.

## Development

Requires Go 1.24+; Python 3 is used for experimental M0 tooling/tests.

```sh
go test ./...
go vet ./...
python3 -m unittest discover -s tools/m0probe -p 'test_*.py'
go build -o bin/drydock ./cmd/drydock
./bin/drydock preflight
```

`preflight` emits JSON and currently always denies qualification. Exit codes:
0 qualified (not currently reachable), 1 unqualified/operational error, 2 invalid
usage. It does not create containers or pull images. Metadata alone cannot
qualify isolation. M0 probes are separate experimental tools with known gaps.
Do not run campaign scripts or archived images as ordinary development tests.

Linux is the supported execution platform. macOS builds do not qualify macOS
execution. Reactor is a future inference target, separate from execution-host
qualification. No automatic push, merge, release or deployment is part of DryDock.

## Project records

- [Authoritative PRD](docs/DryDock_PRD_v0.1.1.docx)
- [Architecture and trust boundaries](docs/architecture.md)
- [Approved decisions](docs/decisions.md)
- [Runtime qualification requirements](docs/runtime-qualification.md)
- [Progress and evidence hashes](docs/progress.md)
- [Evidence interpretation](docs/evidence/README.md)
- [Development and bootstrap notes](docs/development.md)
- [Current handoff](docs/HANDOFF.md)
- [Actionable backlog](https://github.com/admbahm/DryDock/issues)
- [Agent instructions](AGENTS.md)
