# M0 campaign 001

Status: **INCONCLUSIVE** at the host-access prerequisite.

Both the sandboxed SSH attempt and the authorized outside-sandbox retry failed
name resolution with exit code 255. No remote commands or isolation probes ran.
No runtime, image, or execution profile was qualified. No remote cleanup was
needed because no remote resources were created.

`result.json` records observed results; null runtime/image/profile values mean
unobserved, not defaults. `reproduce.sh` repeats only the read-only access check.
It relies on existing operator SSH configuration without copying any of it.

Verify the specimen from this directory with `shasum -a 256 -c manifest.sha256`.
A later successful campaign must receive a new specimen directory.
