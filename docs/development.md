# Development and bootstrap

Go 1.24+ and Python 3 are sufficient for existing local checks. No dependency
installation, model account or Docker daemon is required for the unit suite on
macOS. A Linux preflight test may inspect Docker metadata but creates no jobs.

```sh
gofmt -w cmd/drydock/*.go internal/sandbox/*.go tools/m0probe/*.go
go test ./...
go vet ./...
python3 -m unittest discover -s tools/m0probe -p 'test_*.py'
go build -o bin/drydock ./cmd/drydock
GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -o bin/m0probe ./tools/m0probe
GOOS=linux GOARCH=amd64 go vet ./tools/m0probe
```

Never format `docs/evidence/` snapshots. A cross-build is not a Linux execution
or isolation test. If the environment restricts cache writes, set GOCACHE to an
approved writable directory. Build outputs in `bin/`, Python bytecode caches and
IDE files are ignored. Evidence archives are intentionally versioned, not caches.

The Go module remains `drydock`; changing its import path to the GitHub module
path is deferred rather than mixed into publication housekeeping. No SQLite
implementation/dependency is installed yet.

## Known execution-host bootstrap

The operator manually installed the following on Ubuntu 24.04 amd64 from the
signed Docker/Ubuntu repositories; these are observed versions, not a universal
installation recommendation:

| Package | Version |
| --- | --- |
| docker-ce, docker-ce-cli, docker-ce-rootless-extras | 5:29.8.1-1~ubuntu.24.04~noble |
| containerd.io | 2.3.6-1~ubuntu.24.04~noble |
| slirp4netns | 1.2.1-1build2 |
| libslirp0 | 4.7.0-1ubuntu3.1 |

Operator actions masked system docker.service/docker.socket/containerd.service,
enabled lingering for the ordinary user, and loaded nf_tables. Existing subordinate
IDs and cgroup-v2 cpu/memory/pids delegation needed no modification. AppArmor and
user-namespace restrictions were not disabled. No unrestricted passwordless sudo
was granted. Future privileged changes remain manual operator work; never ask an
agent to handle the operator's password.

Unprivileged setup used the packaged rootless setup tool, user D-Bus and the user
Docker systemd service with `{"log-driver":"none","live-restore":false}`.
Rootless daemon availability is not qualification. The exact user service and
runtime versions are in m0-004. These records include host-specific prototype
paths; they must not become a fixed deployment API.

Runtime qualification is paused. Do not rerun `tools/m0probe/inventory.py` or
`behavior.py` unchanged: they reuse m0-004 names and the output-draining defect
is unresolved. Repair/test the harness separately before considering a new
explicitly identified and authorized campaign. No M1 authorization is implied.
