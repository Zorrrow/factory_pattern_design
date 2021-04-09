locals {
  # Create a list of all disks to create
  disks = flatten([
    for node_name, machine in var.machines : [
      for disk_name, disk in machine.additional_disks : {
        disk = disk
        disk_name = disk_name
        node_name = node_name
      }
    ]
  ])

  lb_backend_servers = flatten([
    for lb_name, loadbalancer in var.loadbalancers : [
      for backend_server in loadbalancer.backend_servers : {
        port = loadbalancer.target_port
        lb_name = lb_name
        server_name = backend_server
      }
    ]
  ])

  # If prefix is set, all resources will be prefixed with "${var.prefix}-"
  # Else don't prefix with anything
  resource-prefix = "%{ if var.prefix != ""}${var.prefix}-%{ endif }"
}

resource "upcloud_network" "private" {
  name = "${local.resource-prefix}k8s-network"
  zone = var.zone

  ip_network {
    address = var.private_network_cidr
    dhcp    = true
    family  = "IPv4"
  }
}

resource "upcloud_storage" "additional_disks" {
  for_each = {
    for disk in local.disks: "${disk.node_name}_${disk.disk_name}" => disk.disk
  }

  size  = each.value.size
  tier  = each.value.tier
  title = "${local.resource-prefix}${each.key}"
  zone  = var.zone
}

resource "upcloud_server" "master" {
  for_each = {
    for name, machine in var.machines :
    name => machine
    if machine.node_type == "master"
  }

  hostname = "${local.resource-prefix}${each.key}"
  plan     = each.value.plan
  cpu      = each.value.plan == null ? each.value.cpu : null
  mem      = each.value.plan == null ? each.value.mem : null
  zone     = var.zone

  template {
  storage = var.template_name
  size    = each.value.disk_size
  }

  # Public network interface
  network_interface {
    type = "public"
  }

  # Private network interface
  network_interface {
    type    = "private"
    network = upcloud_network.private.id
  }

  # Ignore volumes created by csi-driver
  lifecycle {
    ignore_changes = [sto