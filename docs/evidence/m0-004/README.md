# M0 campaign 004

Final result: **INCONCLUSIVE**. No runtime qualification is granted.

The approved unprivileged setup started rootless Docker 29.8.1, containerd
2.3.6, runc 1.5.1, RootlessKit 3.1.0 and slirp4netns 1.2.1 on Linux
6.8.0-142-generic x86_64 with systemd 255. Exact observations and the service
configuration are in `runtime.txt`. The campaign wrote the approved user
`daemon.json`, installed/enabled the rootless user service and context, and
started user D-Bus. No sudo command was executed. System/rootful units remained
masked and inactive. No M1 implementation was performed.

## Observed results and limits

The behavioral image was
`sha256:c93dd948b465f2ba26fd1c9f37c540c310424dd07fb74459f50354bf3e6c76f8`.
Its complete requested profile is recorded in `behavior-inventory/commands.json`.
The earlier inventory-only image is separately identified in `image-id` and
`build.json`; results must not be silently transferred between the two images.

Recorded checks passed for effective cgroup settings, UID/GID, dropped
capabilities, no-new-privileges and seccomp status. Behavioral observations:

- Workspace, temp and shared-memory writes reached ENOSPC at 64, 16 and 8 MiB.
- CPU saturation increased throttling counters within the runner's usage bound.
- Memory allocation exited 137 with Docker reporting OOMKilled.
- Child creation encountered the PID ceiling and increased pids.events.
- Synthetic sentinel direct/traversal/symlink reads and runtime-socket opens
  were denied; the synthetic environment value was absent; sentinel unchanged.
- Tested TCP/UDP destinations were unreachable; controlled IPv4 host listeners
  received no probe traffic after successful positive controls. There was no
  controlled IPv6 listener, so this is not comprehensive network qualification.
- The process-tree probe's cancellation command completed in about 2.10 seconds;
  the container exited and its cgroup was empty/removed. Descendant creation
  was not independently enumerated before cancellation, limiting this evidence.

The output-flood probe then timed out waiting ten seconds for Docker stop.
Its initial forced removal also timed out. The runner stopped; further recovery,
fail-closed fault injection, inode exhaustion and remaining coverage were not
performed. No final PASS is justified by the earlier individual checks.

The runner synchronously waits for stop while it is responsible for draining
attached output. This is a plausible harness-induced backpressure problem, not
an established root cause. The exception also prevented retention of the flood
probe's buffered output. Preserve this gap rather than claiming complete output
or termination evidence. The snapshots in `source/` contain this known defect;
they must not be treated as a qualified production execution broker.

## Cleanup

`cleanup.txt` records a subsequent empty campaign container list and no Docker
job cgroups. `final-cleanup.txt` records removal of the two campaign images and
another empty campaign container list. The rootless daemon remains running as
approved. Remote `/home/adam/drydock-m0-004` holds synthetic tooling and evidence;
it is retained intentionally and contains no injected real credentials.

## Reproduction and integrity

The immutable image inputs are `inventory-rootfs.tar.gz` and
`behavior-rootfs.tar.gz`; decompressing them reproduces the tar hashes recorded
in the build JSON files. Importing with Docker may assign a different image ID
because image creation metadata varies. A new campaign must record its own ID.
The complete argv, deadlines, output limits and observations are in the
inventory/behavior subdirectories. Python standard-library scripts orchestrate
Docker; the synthetic container probe is Go. No host compiler was installed.
This is M0 tooling, not the Go control-plane implementation.

Do not rerun blindly: fix the identified harness issue and review coverage before
starting a new campaign. Never overwrite this specimen or change its final
status. Future profiles/images/configurations require their own observations.

Verify every artifact with `shasum -a 256 -c manifest.sha256` from this directory.
Only synthetic probe data and non-secret configuration/version observations are
included. Host paths, generated IDs and connection coordinates are retained for
attribution; no private keys, SSH configuration or real secret contents appear.
