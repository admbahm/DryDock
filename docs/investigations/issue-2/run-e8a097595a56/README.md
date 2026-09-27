# Issue #2 bounded regression e8a097595a56

Date: 2026-09-27. Result: **PASS for this bounded regression only**.
The owner explicitly authorized this further attempt, including transfer of the
updated runner/helper and the same synthetic inputs to a fresh remote directory.
No sudo, package/configuration changes, qualification campaign, push or merge.

## Verified inputs and execution

Preflight confirmed drydock-exec, UID 1000, rootless Docker 29.8.1,
Linux 6.8.0-142-generic and Python 3.12.3. Exact input/result paths, the run
container label and unique image tag were absent before creation. The new input
directory was mode 0700; all four exact file destinations were checked absent
before transfer. Remote SHA-256 values matched input-hashes.json.

The imported synthetic image was
sha256:a5aacdb7b560048b05ed8fb7a7243d61eedaa7da04c05c9193f889212b9498d7.
A never-started verification container was exported: /probe matched the archived
SHA-256 7076129c12fed9b2078179b20639ec385683c36f05700293a8ec55b5c653105f.
That verification container was removed before the regression. The archived
profile hash matched 34cd0d14a850b55a55ae9deb0bd9f03298c998ad174af2c090135c14b0ac93d1.
The executed sources are preserved under source/ and match the current live
sources at the time this record was created. The runner imported the production
helper. The invocation used a 90-second outer timeout, unchanged ten-second
stop deadline, 42-second case deadline and 1 MiB combined output cap.

## Observed result

- Read 8,388,608 bytes; retained 1,048,576 bytes; truncation true.
- Output-limit termination; stop exit zero in 0.11802839599840809 seconds.
- Attach exit 2; container state exited, Running false.
- Live full-ID scope observed after 65,536 output bytes: cgroup.procs contained
  PID 11977, and cgroup.events reported populated 1, frozen 0.
- Target container ID:
  3c58d642732a531b3031ebd9912f417dd62798708bf06b83c8376b9fba853f00.
- Container removed; empty run-labelled container query; exact observed scope
  subsequently absent, with observable true. The scoped follow-up independently
  checked absence again.

The executed helper starts stop asynchronously after the output threshold and
continues draining. These measurements support that bounded regression behavior
for these exact sources, image, profile and runtime, not universal correctness.

## Cleanup, evidence and boundaries

No container referenced the imported image. It was removed; image inspection by
content ID returned No such image and the unique tag query was empty. Inputs and
all three results were hash-checked immediately before deletion. Both exact
remote directories were removed with rmdir and verified absent. No unrelated
files or runtime settings were touched. cleanup.stdout and operations.json
preserve these checks and command outcomes.

All result files were downloaded and hash-verified before remote deletion.
result.json SHA-256:
e5c671e7be0c48bc220cf3186eaacb0e1eafe948fd99ef2bdadca5488b781067.
manifest.sha256 binds this record, sources, operation log, raw report and retained
output. Operation records include complete argv/scripts, outputs and exit codes;
input-hashes.json and result-hashes.json bind transferred and collected bytes.

Earlier Issue #2 evidence, including INCONCLUSIVE run 86a56976e3cf, remains
unchanged. This success does not establish the cause of that earlier observation
failure. Historical m0-004 remains INCONCLUSIVE; M0 remains UNQUALIFIED; M1 remains
NOT STARTED. No Issue #3 or m0-005 work occurred. Issue #2/PR #7 still require
review and separately authorized publication/merge; no issue was closed.
