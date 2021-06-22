# vSphere CSI Driver

vSphere CSI driver allows you to provision volumes over a vSphere deployment. The Kubernetes historic in-tree cloud provider is deprecated and will be removed in future versions.

## Prerequisites

The vSphere user for CSI driver requires a set of privileges to perform Cloud Native Storage operations. Follow the [official guide](https://vsphere-csi-driver.sigs.k8s.io/driver-deployment/prerequisites.html#roles_and_privileges) to configure those.

## Kubespray configuration

To enable vSphere CSI driver, uncomment the `vsphere_csi_enabled` option in `group_vars/all/vsphere.yml` and set it to `true`.

To set the number of replicas for the vSphere CSI controller, you can change `vsphere_csi_controller_replicas` option in `group_vars/all/vsphere.yml`.

You need to source the vSphere credentials you use to deploy your machines that will host Kubernetes.

| Variable                                        | Required | Type    | Choices         | Default                 | Comment                                                                                                                     |
|-------------------------------------------------|----------|---------|-----------------|-------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| external_vsphere_vcenter_ip                     | TRUE     | string  |                 |                         | IP/URL of the vCenter                                                                                                       |
| external_vsphere_vcenter_port                   | TRUE     | string  |                 | "443"                   | Port of the vCenter API                                                                                                     |
| external_vsphere_insecure                       | TRUE     | string  | "true", "false" | "true"                  | set to "true" if the host above uses a self-signed cert                                                                     |
| external_vsphere_user                           | TRUE     | string  |                 |                         | User name for vCenter with required privileges (Can also be specified with the `VSPHERE_USER` environment variable)         |
| external_vsphere_password                       | TRUE     | string  |                 |                         | Password for vCenter (Can also be specified with the `VSPHERE_PASSWORD` environment variable)                               |
| external_vsphere_datacenter                     | TRUE     | string  |                 |                         | Datacenter name to use                                                                                                      |
| external_vsphere_kubernetes_cluster_id          | TRUE     | string  |                 | "kubernetes-cluster-id" | Kubernetes cluster ID to use                                                                                                |
| external_vsphere_version                        | TRUE     | string  |                 | "6.7u3"                 | Vmware Vsphere version where located all VMs                                                                                |
| external_vsphere_cloud_controller_image_tag     | TRUE     | string  |                 | "latest"                | Kubernetes cluster ID to use                                                                   