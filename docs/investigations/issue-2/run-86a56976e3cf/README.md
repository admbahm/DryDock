# Issue #2 bounded regression 86a56976e3cf

Date: 2026-09-27. Disposition: **INCONCLUSIVE**. This is not an M0 campaign.
The owner authorized a bounded rerun, then explicitly authorized the four-file
payload and destination after automatic approval review initially rejected the
transfer. That rejected request made no remote changes. No sudo was used.

## Observations

- Preflight confirmed drydock-exec, UID 1000, rootless Docker 29.8.1,
  Linux 6.8.0-142-generic and Python 3.12.3.
- The exact run input/result directories, run container label and image tag were
  absent before creation. Inputs were transferred into a fresh mode-0700 directory.
- Remote hashes matched input-hashes.json for both Python sources, the immutable
  archived profile and synthetic rootfs. A never-started verification container
  was exported: /probe matched SHA-256
  7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f.
  That verification container was removed before the output regression.
- The regression used a 90-second outer timeout, unchanged ten-second stop
  deadline and 1 MiB combined output cap. It exited 1 with INCONCLUSIVE.
- It discovered scope docker-ac36d12b7a1c247231d80857b7a5e40c9270d87604bf5c470a8595ae535dca99.scope,
  but observe_cgroup rejected its membership with
  `RuntimeError('target cgroup has no observable live processes')`.
- Zero output bytes were read. No stop request was issued. This attempt does
  not demonstrate output flooding, concurrent drain or bounded Docker stop.

A startup timing race is a hypothesis, not an established explanation. The error
can mean empty or invalid membership (including zero-valued PIDs); raw
cgroup.procs contents were not preserved by the observer. Do not claim which
condition occurred. The runner failed closed instead of accepting missing proof.

## Cleanup and retained evidence

The runner removed the target container. A subsequent independent scoped check
confirmed no run-labelled containers and absence of the exact recorded scope.
No containers referenced the imported image; it was removed, and inspecting its
content ID then returned No such image. All four transferred inputs and all
three result files were hash-checked immediately before deletion. Both remote
directories were removed with rmdir and verified absent. No unrelated paths or
runtime configuration were changed. See cleanup.stdout and operations.json.

All three result files were copied locally and matched remote SHA-256 values
before remote deletion. result.json SHA-256:
06d59aa3bb91db6bb57a5780b767bbce001d32030d2eda400bda1a911047411a.
source/ binds the exact executed runner/helper. operations.json records commands,
remote scripts, exit statuses and outputs for prechecks, transfers, image
verification, execution, collection and cleanup. manifest.sha256 binds this record.

The post-run cleanup observation does not change the regression's INCONCLUSIVE
classification: positive live membership and output cancellation were not proved.
No second attempt was made. A local observer/readiness investigation is next;
any later remote attempt requires a new identity and explicit authorization.

Historical m0-001 through m0-004 and the earlier Issue #2 JSON are unchanged.
m0-004 remains INCONCLUSIVE; M0 remains UNQUALIFIED; M1 remains NOT STARTED.
No Issue #3, m0-005, qualification campaign, push or merge occurred.
