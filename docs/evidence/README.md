# Runtime evidence specimens

Each `m0-NNN/` directory is a closed, immutable campaign specimen. Its README and
result describe the final disposition; a SHA-256 manifest binds the listed files.
The manifest's own digest is recorded in [progress](../progress.md). Hashes detect
changes relative to those references; they are not signatures or protection from
a compromised host/administrator.

| Campaign | Final result | Observed stopping point |
| --- | --- | --- |
| m0-001 | INCONCLUSIVE | Execution hostname could not resolve |
| m0-002 | INCONCLUSIVE | SSH succeeded; noninteractive privileged bootstrap unavailable |
| m0-003 | INCONCLUSIVE | Setup tool reported nf_tables prerequisite missing; operator later loaded it |
| m0-004 | INCONCLUSIVE | Output-flood termination command exceeded ten seconds |

PASS means a specific check was demonstrated for the recorded configuration.
FAIL means observed behavior contradicted a requirement. INCONCLUSIVE means
insufficient evidence, including missing observations or infrastructure/harness
errors. None of these campaigns qualifies the runtime. Per-probe PASS entries
in m0-004 do not override its final INCONCLUSIVE result.

m0-004 contains command records, outputs, inspection data, runtime versions,
source snapshots and compressed synthetic image inputs. Earlier campaigns stopped
before runtime probes and have smaller records. Source snapshots intentionally
preserve known bugs. Archived binaries are synthetic Linux probes, not releases.
Do not execute archives or reproduction scripts merely to verify integrity.

Verify from each campaign directory with `shasum -a 256 -c manifest.sha256`
(or `sha256sum -c manifest.sha256` on Linux). Also compare the manifest digest
against progress. Keep paths, bytes and manifests unchanged. Any correction,
interpretation or repaired harness belongs outside a historical specimen. A new
campaign needs a new identity and must record exact runtime/profile/image/config.

Public evidence retains ordinary hostnames, private network addresses, user IDs,
non-secret home/runtime paths and versions for reproducibility. Real credentials
must never be collected. If sensitive material is discovered, stop publication
and propose a remedy retaining private originals and explicit derivation/provenance;
never silently sanitize or regenerate the historical manifest.
