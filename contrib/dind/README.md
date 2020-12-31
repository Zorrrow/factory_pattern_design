
# Kubespray DIND experimental setup

This ansible playbook creates local docker containers
to serve as Kubernetes "nodes", which in turn will run
"normal" Kubernetes docker containers, a mode usually
called DIND (Docker-IN-Docker).

The playbook has two roles:

- dind-host: creates the "nodes" as containers in localhost, with
  appropriate settings for DIND (privileged, volume mapping for dind
  storage, etc).
- dind-cluster: customizes each node container to have required
  system packages installed, and some utils (swapoff, lsattr)
  symlinked to /bin/true to ease mimicking a real node.

This playbook has been test with Ubuntu 16.04 as host and ubuntu:16.04
as docker images (note that dind-cluster has specific customization
for these images).

The playbook also creates a `/tmp/kubespray.dind.inventory_builder.sh`
helper (wraps up running `contrib/inventory_builder/inventory.py` with
node containers IPs and prefix).

## Deploying

See below for a complete successful run:

1. Create the node containers

```shell
# From the kubespray root dir
cd contrib/dind
pip install -r requirements.txt

ansible-playbook -i hosts dind-cluster.yaml

# Back to kubespray root
cd ../..
```

NOTE: if the playbook run fails with something like below error
message, you may need to specifically set `ansible_python_interpreter`,
see `./hosts` file for an example expanded localhost entry.

```shell
failed: [localhost] (item=kube-node1) => {"changed": false, "item": "kube-node1", "msg": "Failed to import docker or docker-py - No module named requests.exceptions. Try `pip install docker` or `pip install docker-py` (Python 2.6)"}
```

2. Customize kubespray-dind.yaml

Note that there's coupling between above created node containers
and `kubespray-dind.yaml` settings, in particular regarding selected `node_distro`
(as set in `group_vars/all/all.yaml`), and docker settings.

```shell
$EDITOR contrib/dind/kubespray-dind.yaml
```

3. Prepare the inventory and run the playbook

```shell
INVENTORY_DIR=inventory/local-dind
mkdir -p ${INVENTORY_DIR}
rm -f ${INVENTORY_DIR}/hosts.ini
CONFIG_FILE=${INVENTORY_DIR}/hosts.ini /tmp/kubespray.dind.inventory_builder.sh

ansible-playbook --become -e ansible_ssh_user=debian -i ${INVENTORY_DIR}/hosts.ini cluster.yml --extra-vars @contrib/dind/kubespray-dind.yaml
```

NOTE: You could also test other distros without editing files by
passing `--extra-vars` as per below commandline,
replacing `DISTRO` by either `debian`, `ubuntu`, `centos`, `fedora`:

```shell
cd contrib/dind
ansible-playbook -i hosts dind-cluster.yaml --extra-vars node_distro=DISTRO

cd ../..
CONFIG_FILE=inventory/local-dind/hosts.ini /tmp/kubespray.dind.inventory_builder.sh
ansible-playbook --become -e ansible_ssh_user=DISTRO -i inventory/local-dind/hosts.ini cluster.yml --extra-vars @contrib/dind/kubespray-dind.yaml --extra-vars bootstrap_os=DISTRO
```

## Resulting deployment

See below to get an idea on how a completed deployment looks like,
from the host where you ran kubespray playbooks.

### node_distro: debian
