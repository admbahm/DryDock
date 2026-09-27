# M0 campaign 003

**INCONCLUSIVE** at the rootless setup prerequisite.

SSH confirmed the installed runtime package versions and masked/inactive system
services. `dockerd-rootless-setuptool.sh check` exited 1 and requested loading
`nf_tables`. Its suggested iptables-check bypass was not used. No privileged
commands ran. No user daemon configuration or containers were created, so no
campaign cleanup was required. The user D-Bus service was observed inactive.

The diagnostic is evidence of a setup blocker, not an independently established
kernel-module state or a runtime isolation failure. No image/profile qualified.
`prerequisite-output.txt` removes terminal color escapes from tool output.
`reproduce.sh` repeats the prerequisite check; remediation text is output only.

Verify with `shasum -a 256 -c manifest.sha256`. No credentials, SSH keys or
secret contents are included. Earlier campaign specimens remain unchanged.
