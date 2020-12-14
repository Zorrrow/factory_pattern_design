# Deploy a Production Ready Kubernetes Cluster

![Kubernetes Logo](https://raw.githubusercontent.com/kubernetes-sigs/kubespray/master/docs/img/kubernetes-logo.png)

If you have questions, check the documentation at [kubespray.io](https://kubespray.io) and join us on the [kubernetes slack](https://kubernetes.slack.com), channel **\#kubespray**.
You can get your invite [here](http://slack.k8s.io/)

- Can be deployed on **[AWS](docs/aws.md), GCE, [Azure](docs/azure.md), [OpenStack](docs/openstack.md), [vSphere](docs/vsphere.md), [Equinix Metal](docs/equinix-metal.md) (bare metal), Oracle Cloud Infrastructure (Experimental), or Baremetal**
- **Highly available** cluster
- **Composable** (Choice of the network plugin for instance)
- Supports most popular **Linux distributions**
- **Continuous integration tests**

## Quick Start

Below are several ways to use Kubespray to deploy a Kubernetes cluster.

### Ansible

#### Usage

Install Ansible according to [Ansible installation guide](/docs/ansible.md#installing-ansible)
then run the following steps:

```ShellSession
# Copy ``inventory/sample`` as ``inventory/mycluster``
cp -rfp inventory/sample inventory/mycluster

# Update Ansible inventory file with inventory builder
declare -a IPS=(10.10.1.3 10.10.1.4 10.10.1.5)
CONFIG_FILE=inventory/mycluster/hosts.yaml python3 contrib/inventory_builder/inventory.py ${IPS[@]}

# Review and change parameters under ``inventory/mycluster/group_vars``
cat inventory/mycluster/group_vars/all/all.yml
cat inventory/mycluster/group_vars/k8s_cluster/k8s-cluster.yml

# Deploy Kubespray with Ansible Playbook - run the playbook as root
# The option `--become` is required, as for example writing SSL keys in /etc/,
# installing packages and interacting with various systemd daemons.
# Without --become the playbook will fail to run!
ansible-playbook -i inventory/mycluster/hosts.yaml  --become --become-user=root cluster.yml
```

Note: When Ansible is already installed via system packages on the control node,
Python packages installed via `sudo pip install -r requirements.txt` will go to
a different directory tree (e.g. `/usr/local/lib/python2.7/dist-packages` on
Ubuntu) from Ansible's (e.g. `/usr/lib/python2.7/dist-packages/ansible` still on
Ubuntu). As a consequence, the `ansible-playbook` command will fail with:

```raw
ERROR! no action detected in task. This often indicates a misspelled module name, or incorrect module path.
```

This likely indicates that a task depends on a module present in ``requirements.txt``.

One way of addressing this is to uninstall the system Ansible package then
reinstall Ansible via ``pip``, but this not always possible and one must
take care regarding package versions.
A workaround consists of setting the `ANSIBLE_LIBRARY`
and `ANSIBLE_MODULE_UTILS` environment variables respectively to
the `ansible/modules` and `ansible/module_utils` subdirectories of the ``pip``
installation location, which is the ``Location`` shown by running
`pip show [package]` before executing `ansible-playbook`.

A simple way to ensure you get all the correct version of Ansible is to use
the [pre-built docker image from Quay](https://quay.io/repository/kubespray/kubespray?tab=tags).
You will then need to use [bind mounts](https://docs.docker.com/storage/bind-mounts/)
to access the inventory and SSH key in the container, like this:

```ShellSession
git checkout v2.21.0
docker pull quay.io/kubespray/kubespray:v2.21.0
docker run --rm -it --mount type=bind,source="$(pwd)"/inventory/sample,dst=/inventory \
  --mount type=bind,source="${HOME}"/.ssh/id_rsa,dst=/root/.ssh/id_rsa \
  quay.io/kubespray/kubespray:v2.21.0 bash
# Inside the container you may now run the kubespray playbooks:
ansible-playbook -i /inventory/inventory.ini --private-key /root/.ssh/id_rsa cluster.yml
```

### Vagrant

For Vagrant we need to install Python dependencies for provisioning tasks.
Check that ``Python`` and ``pip`` are installed:

```ShellSession
python -V && pip -V
```

If this returns the version of the software, you're good to go. If not, download and install Python from here <https://www.python.org/downloads/source/>

Install Ansible according to [Ansible installation guide](/docs/ansible.md#installing-ansible)
then run the following step:

```ShellSession
vagrant up
```

## Documents

- [Requirement