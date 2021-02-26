data "openstack_images_image_v2" "vm_image" {
  count = var.image_uuid == "" ? 1 : 0
  most_recent = true
  name = var.image
}

data "openstack_images_image_v2" "gfs_image" {
  count = var.image_gfs_uuid == "" ? var.image_uuid == "" ? 1 : 0 : 0
  most_recent = true
  name = var.image_gfs == "" ? var.image : var.image_gfs
}

data "openstack_images_image_v2" "image_master" {
  count = var.image_master_uuid == "" ? var.image_uuid == "" ? 1 : 0 : 0
  name = var.image_master == "" ? var.image : var.image_master
}

data "cloudinit_config" "cloudinit" {
  part {
    content_type =  "text/cloud-config"
    content = templatefile("${path.module}/templates/cloudinit.yaml.tmpl", {
      # template_file doesn't support lists
      extra_partitions = ""
    })
  }
}

data "openstack_networking_network_v2" "k8s_network" {
  count = var.use_existing_network ? 1 : 0
  name  = var.network_name
}

resource "openstack_compute_keypair_v2" "k8s" {
  name       = "kubernetes-${var.cluster_name}"
  public_key = chomp(file(var.public_key_path))
}

resource "openstack_networking_secgroup_v2" "k8s_master" {
  name                 = "${var.cluster_name}-k8s-master"
  description          = "${var.cluster_name} - Kubernetes Master"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_v2" "k8s_master_extra" {
  count                = "%{if var.extra_sec_groups}1%{else}0%{endif}"
  name                 = "${var.cluster_name}-k8s-master-${var.extra_sec_groups_name}"
  description          = "${var.cluster_name} - Kubernetes Master nodes - rules not managed by terraform"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "k8s_master" {
  count             = length(var.master_allowed_remote_ips)
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = "6443"
  port_range_max    = "6443"
  remote_ip_prefix  = var.master_allowed_remote_ips[count.index]
  security_group_id = openstack_networking_secgroup_v2.k8s_master.id
}

resource "openstack_networking_secgroup_rule_v2" "k8s_master_ports" {
  count             = length(var.master_allowed_ports)
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = lookup(var.master_allowed_ports[count.index], "protocol", "tcp")
  port_range_min    = lookup(var.master_allowed_ports[count.index], "port_range_min")
  port_range_max    = lookup(var.master_allowed_ports[count.index], "port_range_max")
  remote_ip_prefix  = lookup(var.master_allowed_ports[count.index], "remote_ip_prefix", "0.0.0.0/0")
  security_group_id = openstack_networking_secgroup_v2.k8s_master.id
}

resource "openstack_networking_secgroup_v2" "bastion" {
  name                 = "${var.cluster_name}-bastion"
  count                = var.number_of_bastions != "" ? 1 : 0
  description          = "${var.cluster_name} - Bastion Server"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "bastion" {
  count             = var.number_of_bastions != "" ? length(var.bastion_allowed_remote_ips) : 0
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = "22"
  port_range_max    = "22"
  remote_ip_prefix  = var.bastion_allowed_remote_ips[count.index]
  security_group_id = openstack_networking_secgroup_v2.bastion[0].id
}

resource "openstack_networking_secgroup_rule_v2" "k8s_bastion_ports" {
  count             = length(var.bastion_allowed_ports)
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = lookup(var.bastion_allowed_ports[count.index], "protocol", "tcp")
  port_range_min    = lookup(var.bastion_allowed_ports[count.index], "port_range_min")
  port_range_max    = lookup(var.bastion_allowed_ports[count.index], "port_range_max")
  remote_ip_prefix  = lookup(var.bastion_allowed_ports[count.index], "remote_ip_prefix", "0.0.0.0/0")
  security_group_id = openstack_networking_secgroup_v2.bastion[0].id
}

resource "openstack_networking_secgroup_v2" "k8s" {
  name                 = "${var.cluster_name}-k8s"
  description          = "${var.cluster_name} - Kubernetes"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "k8s" {
  direction         = "ingress"
  ethertype         = "IPv4"
  remote_group_id   = openstack_networking_secgroup_v2.k8s.id
  security_group_id = openstack_networking_secgroup_v2.k8s.id
}

resource "openstack_networking_secgroup_rule_v2" "k8s_allowed_remote_ips" {
  count             = length(var.k8s_allowed_remote_ips)
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = "22"
  port_range_max    = "22"
  remote_ip_prefix  = var.k8s_allowed_remote_ips[count.index]
  security_group_id = openstack_networking_secgroup_v2.k8s.id
}

resource "openstack_networking_secgroup_rule_v2" "egress" {
  count             = length(var.k8s_allowed_egress_ips)
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = var.k8s_allowed_egress_ips[count.index]
  security_group_id = openstack_networking_secgroup_v2.k8s.id
}

resource "openstack_networking_secgroup_v2" "worker" {
  name                 = "${var.cluster_name}-k8s-worker"
  description          = "${var.cluster_name} - Kubernetes worker nodes"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_v2" "worker_extra" {
  count                = "%{if var.extra_sec_groups}1%{else}0%{endif}"
  name                 = "${var.cluster_name}-k8s-worker-${var.extra_sec_groups_name}"
  description          = "${var.cluster_name} - Kubernetes worker nodes - rules not managed by terraform"
  delete_default_rules = true
}

resource "openstack_networking_secgroup_rule_v2" "worker" {
  count             = length(var.worker_allowed_ports)
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = lookup(var.worker_allowed_ports[count.index], "protocol", "tcp")
  port_range_min    = lookup(var.worker_allowed_ports[count.index], "port_range_min")
  port_range_max    = lookup(var.worker_allowed_ports[count.index], "port_range_max")
  remote_ip_prefix  = lookup(var.worker_allowed_ports[count.index], "remote_ip_prefix", "0.0.0.0/0")
  security_group_id = openstack_networking_secgroup_v2.worker.id
}

resource "openstack_compute_servergroup_v2" "k8s_master" {
  count    = var.master_server_group_policy != "" ? 1 : 0
  name     = "k8s-master-srvgrp"
  policies = [var.master_server_group_policy]
}

resource "openstack_compute_servergroup_v2" "k8s_node" {
  count    = var.node_server_group_policy != "" ? 1 : 0
  name     = "k8s-node-srvgrp"
  policies = [var.node_server_group_policy]
}

resource "openstack_compute_servergroup_v2" "k8s_etcd" {
  count    = var.etcd_server_group_policy != "" ? 1 : 0
  name     = "k8s-etcd-srvgrp"
  policies = [var.etcd_server_group_policy]
}

resource "openstack_compute_servergroup_v2" "k8s_node_additional" {
  for_each = var.additional_server_groups
  name     = "k8s-${each.key}-srvgrp"
  policies = [each.value.policy]
}

locals {
# master groups
  master_sec_groups = compact([
    openstack_networking_secgroup_v2.k8s_master.id,
    openstack_networking_secgroup_v2.k8s.id,
    var.extra_sec_groups ?openstack_networking_secgroup_v2.k8s_master_extra[0].id : "",
  ])
# worker groups
  worker_sec_groups = compact([
    opensta