# Initial public publication review

Scope: all current source, tests, docs, instruction/configuration files, tracked
and untracked candidates, ignored IDE/build/cache files, PRD ZIP metadata and
relationships, and both compressed evidence image inputs. No files were staged
before this review. The repository had no commits or configured remote.

Text review and credential-pattern scans found no passwords, API tokens, private
keys, credential-bearing URLs or copied SSH authentication material in publication
candidates. Docker inspection environment/mount fields and recorded runtime
configuration were reviewed; synthetic marker values are explicitly synthetic.
Socket paths are text, not live sockets. No runtime database, socket, package cache
or IDE state is included. The two rootfs archives each contain only one regular
`probe` executable. Binary string scans found no private-key/token patterns or
absolute developer home paths. PRD metadata identifies DryDock, contains no
personal author data, and has no external relationships. This is a proportionate
publication review, not proof that every possible secret encoding is absent.

Deliberately retained: private IP 192.168.50.99, hostname drydock-exec, generic user
adam/UID 1000, package/runtime/kernel versions, generated image/container IDs,
and non-secret home/cgroup/runtime paths. These describe the synthetic campaign
and were judged appropriate reproducibility metadata for this public project.
No historical specimen was redacted, moved, formatted or rehashed for publication.
All four manifest digests and listed artifact hashes match their prior references.

Ignored: bin/ generated binaries and tar inputs, .idea/, *.iml, __pycache__/ and
.local/. The committed image archives under evidence are deliberate provenance
artifacts. The authoritative PRD was moved byte-for-byte under docs; its SHA-256
remains a80aba5eabc20f8a1f41c0b5d42cc0e62eabe95bf9989adc6d99b9c2c7c326e7.

GitHub ownership and administrative settings remain operator-controlled. Only
explicitly requested issues/labels and initial source publication are in scope.
No collaborators, integrations, Actions, secrets or protections were configured
by this work.

Staged review: 99 intended files; generated/IDE/cache files excluded. The full
whitespace check reports one pre-existing trailing space in historical
m0-004/runtime.txt (ExecStart). It is intentionally preserved for hash integrity.
The whitespace check excluding immutable specimens passes.
