#!/bin/bash
set -euxo pipefail

# Cleanup vagrant VMs to avoid name conflicts

apt-get install -y libvirt-clients

for i in $(virsh list --name)
do
    virsh destroy "$i"
    virsh undefine "$i"
done


# Cleanup domain volumes
for i in $(virsh vol-list