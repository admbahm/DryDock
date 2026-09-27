# Execution host qualification

Status: campaign m0-004 installed/configured the approved rootless user service
and ran synthetic probes. It stopped as INCONCLUSIVE on an output-flood stop
command timeout. No runtime/profile is qualified. Cleanup found no remaining
campaign containers or Docker job cgroups; the approved daemon remains running.
See [the specimen and evidence limits](evidence/m0-004/README.md).
Earlier campaigns remain unchanged.

The preflight command checks Linux and, on Linux, bounded Docker metadata for
a Linux rootless engine. It always denies qualification; experimental campaign probes are separate and
have not established a qualified configuration.
Docker metadata is diagnostic information, not an authorization credential.

Before implementing task dispatch, select the Linux host, pinned verification
image, runtime version, and explicit resource ceilings. Confirm that the Docker
endpoint represents that selected host; remote contexts must not accidentally
qualify a different execution environment.

Qualification must collect observed results for:

| Boundary | Required observable proof |
| --- | --- |
| Host access | Jobs cannot read host sentinel fixtures, controller state, home, credentials, devices or the runtime socket |
| Network | IPv4/IPv6 outbound and host-service access denied |
| Filesystem | Read-only root; only approved writable paths; traversal and symlink escapes denied |
| Resources | CPU, memory, writable storage and process limits demonstrably enforced |
| Output/time | Excess output bounded; deadlines stop work |
| Cancellation | Entire process tree terminates within ten seconds |
| Recovery | Named orphan jobs can be found and reaped before explicit resume |
| Credentials | Environment and mounts exclude controller/provider secrets |

Record image/runtime/configuration identity and results. A configuration change
requires requalification. Missing or inconclusive observations cannot pass.
The probes operate on synthetic sentinels, never actual secrets.

Do not substitute unrestricted host subprocesses if a boundary cannot be
enforced. Do not assume Docker's defaults enforce the required limits.
