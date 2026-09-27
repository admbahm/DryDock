#!/bin/sh
# Read-only host-access reproduction; no installation or qualification grant.
# Requires the operator-provisioned SSH trust and authentication configuration.
exec ssh -o BatchMode=yes -o ForwardAgent=no -o StrictHostKeyChecking=yes -o ConnectTimeout=10 adam@drydock-exec 'hostname; uname -srm; cat /etc/os-release; id -u; id -un; command -v docker; sudo -n true'
