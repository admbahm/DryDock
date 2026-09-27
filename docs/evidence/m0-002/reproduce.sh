#!/bin/sh
# Read-only prerequisite check; relies on operator-provisioned SSH authentication.
exec ssh -o BatchMode=yes -o ForwardAgent=no -o StrictHostKeyChecking=yes -o ConnectTimeout=10 adam@192.168.50.99 'hostname; uname -srm; cat /etc/os-release; id -u; id -un; command -v docker; sudo -n true'
