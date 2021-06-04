
# OpenStack

## Known compatible public clouds

Kubespray has been tested on a number of OpenStack Public Clouds including (in alphabetical order):

- [Auro](https://auro.io/)
- [Betacloud](https://www.betacloud.io/)
- [CityCloud](https://www.citycloud.com/)
- [DreamHost](https://www.dreamhost.com/cloud/computing/)
- [ELASTX](https://elastx.se/)
- [EnterCloudSuite](https://www.entercloudsuite.com/)
- [FugaCloud](https://fuga.cloud/)
- [Infomaniak](https://infomaniak.com)
- [Open Telekom Cloud](https://cloud.telekom.de/) : requires to set the variable `wait_for_floatingip = "true"` in your cluster.tfvars
- [OVHcloud](https://www.ovhcloud.com/)
- [Rackspace](https://www.rackspace.com/)
- [Ultimum](https://ultimum.io/)
- [VexxHost](https://vexxhost.com/)
- [Zetta](https://www.zetta.io/)

## The in-tree cloud provider

To deploy Kubespray on [OpenStack](https://www.openstack.org/) uncomment the `cloud_provider` option in `group_vars/all/all.yml` and set it to `openstack`.

After that make sure to source in your OpenStack credentials like you would do when using `nova-client` or `neutron-client` by using `source path/to/your/openstack-rc` or `. path/to/your/openstack-rc`.

For those who prefer to pass the OpenStack CA certificate as a string, one can
base64 encode the cacert file and store it in the variable `openstack_cacert`.

The next step is to make sure the hostnames in your `inventory` file are identical to your instance names in OpenStack.
Otherwise [cinder](https://wiki.openstack.org/wiki/Cinder) won't work as expected.

Unless you are using calico or kube-router you can now run the playbook.

## The external cloud provider

The in-tree cloud provider is deprecated and will be removed in a future version of Kubernetes. The target release for removing all remaining in-tree cloud providers is set to 1.21.

The new cloud provider is configured to have Octavia by default in Kubespray.

- Enable the new external cloud provider in `group_vars/all/all.yml`:

  ```yaml
  cloud_provider: external
  external_cloud_provider: openstack
  ```

- Enable Cinder CSI in `group_vars/all/openstack.yml`:

  ```yaml
  cinder_csi_enabled: true
  ```

- Enable topology support (optional), if your openstack provider has custom Zone names you can override the default "nova" zone by setting the variable `cinder_topology_zones`

  ```yaml
  cinder_topology: true
  ```

- Enabling `cinder_csi_ignore_volume_az: true`, ignores volumeAZ and schedules on any of the available node AZ.

  ```yaml
  cinder_csi_ignore_volume_az: true
  ```

- If you are using OpenStack loadbalancer(s) replace the `openstack_lbaas_subnet_id` with the new `external_openstack_lbaas_subnet_id`. **Note** The new cloud provider is using Octavia instead of Neutron LBaaS by default!
- Enable 3 feature gates to allow migration of all volumes and storage classes (if you have any feature gates already set just add the 3 listed below):

  ```yaml
  kube_feature_gates:
  - CSIMigration=true
  - CSIMigrationOpenStack=true
  - ExpandCSIVolumes=true
  ```

- If you are in a case of a multi-nic OpenStack VMs (see [kubernetes/cloud-provider-openstack#407](https://github.com/kubernetes/cloud-provider-openstack/issues/407) and [#6