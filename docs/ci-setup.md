# CI Setup

## Pipeline

1. build: build a docker image to be used in the pipeline
2. unit-tests: fast jobs for fast feedback (linting, etc...)
3. deploy-part1: small number of jobs to test if the PR works with default settings
4. deploy-part2: slow jobs testing different platforms, OS, settings, CNI, etc...
5. deploy-part3: very slow jobs (upgrades, etc...)

## Runners

Kubespray has 3 types of GitLab runners:

- packet runners: used for E2E jobs (usually long), running on Equinix Metal (ex-packet), on kubevirt managed VMs
- light runners: used for short lived jobs, running on Equinix Metal (ex-packet), as managed pods
- auto scaling runners (managed via docker-machine on Equinix Metal): used for on-demand resources, see [GitLab docs](https://docs.gitlab.com/runner/configuration/autoscale.html) for more info

## Vagrant

Vagrant jobs are using the [quay.io/kubespray/vagrant](/test-infra/vagrant-docker/Dockerfile) docker image with `/var/run/libvirt/libvirt-sock` exposed from the host, allowing the container to boot VMs on the host.

## CI Variables

In CI we have a set of overrides we use to ensure greater success of our CI jobs and avoid throttling by various APIs we depend on. See:

- [Docker mirrors](/tests/common/_docker_hub_registry_mirror.yml)
- [Test settings](/tests/common/_kubespray_test_settings.yml)

## CI Environment

The CI packet and light runners are deployed on a kubernetes cluster on Equinix Metal. The cluster is deployed with kubespray itself and maintained by the kubespray maintainers.

The following files are used for that inventory:

### cluster.tfvars

```ini
# your Kubernetes cluster name here
cluster_name = "ci"

# Your Equinix Metal project ID. See https://metal.equinix.com/developers/docs/accounts/
equinix_metal_project_id = "_redacted_"

# The public SSH key to be uploaded into authorized_keys in bare metal Equinix Metal nodes provisioned
# leave this value blank if the public key is already setup in the Equinix Metal project
# Terraform will complain if the public key is setup in Equinix Metal
public_key_path = "~/.ssh/id_rsa.pub"

# cluster location
facility = "am6"

# standalone etcds
number_of_etcd = 0

plan_etcd = "t1.small.x86"

# masters
number_of_k8s_masters = 1

number_of_k8s_masters_no_etcd = 0

plan_k8s_masters = "c3.small.x86"

plan_k8s_masters_no_etcd = "t1.small.x86"

# nodes
number_of_k8s_nodes = 1

plan_k8s_nodes = "c3.medium.x86"
```

### group_vars/all/mirrors.yml

```yaml
---
docker_registry_mirrors:
  - "https://mirror.gcr.io"

containerd_grpc_max_recv_message_size: 16777216
containerd_grpc_max_send_message_size: 16777216

containerd_registries:
  "docker.io":
    - "https://mirror.gcr.io"
    - "https://registry-1.docker.io"

containerd_max_container_log_line_size: -1

crio_registries_mirrors:
  - prefix: docker.io
    insecure: false
    blocked: false
    location: registry-1.docker.io
    mirrors:
      - location: mirror.gcr.io
        insecure: false

netcheck_agent_image_repo: "{{ quay_image_repo }}/kubespray/k8s-netchecker-agent"
netcheck_server_image_repo: "{{ quay_image_repo }}/kubespray/k8s-netchecker-server"

nginx_image_repo: "{{ quay_image_repo }}/kubespray/nginx"
```

### group_vars/all/settings.yml

```yaml
---
# Networking setting
kube_service_addresses: 172.30.0.0/18
kube_pods_subnet: 172.30.64.0/18
kube_network_plugin: calico
# avoid overlap with CI jobs deploying nodelocaldns
nodelocaldns_ip: 169.254.255.100

# ipip: False
calico_ipip_mode: "Never"
calico_vxlan_mode: "Never"
calico_network_backend: "bird"
calico_wireguard_enable