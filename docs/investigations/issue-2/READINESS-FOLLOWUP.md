# Local readiness follow-up after 86a56976e3cf

The completed remote attempt remains INCONCLUSIVE and unchanged. Its exact
failure cause cannot be recovered: raw cgroup membership was not retained.
Source inspection establishes that the observer was invoked when a scope was
first discovered, before any attached output had been read. A startup race is
plausible, but has not been proved for that attempt.

The live helper now observes readiness after output consumption begins and
retries pending observations within the existing drain loop. Output keeps
being drained. No stop or case deadline is increased. Missing/error observations
still cannot pass, and cleanup still requires exact scope absence after a
positive live observation.

The observer retains raw cgroup.procs and cgroup.events text. It uses the kernel's
`populated` field to establish live processes in the scope or its descendants;
direct cgroup.procs membership can be empty for a populated subtree. A populated
value of 0 is pending, never live evidence. Malformed/missing event fields and
read errors fail closed. Only the last observation and an attempt count are
retained, avoiding an unbounded history.

Source: [Linux kernel cgroup-v2 documentation](https://www.kernel.org/doc/html/v6.9/admin-guide/cgroup-v2.html).

New local tests cover pending-to-live observation with uninterrupted draining,
a never-populated scope that cannot pass even if later absent, retained raw
observations, malformed population values, and full container-ID binding.
The full local suite has 19 passing tests. Python compilation and diff checks
pass; historical evidence and the completed run manifest verify unchanged.
No further remote attempt has executed this revision. It needs a new run
identity and authorized transfer/execution; neither earlier report is evidence
for this revision. No push or merge occurred. M0 remains UNQUALIFIED and M1
remains NOT STARTED.
