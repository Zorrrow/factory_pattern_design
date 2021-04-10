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
    ignore_changes = [storage_devices]
  }

  firewall  = var.firewall_enabled

  dynamic "storage_devices" {
    for_each = {
      for disk_key_name, disk in upcloud_storage.additional_disks :
        disk_key_name => disk
        # Only add the disk if it matches the node name in the start of its name
        if length(regexall("^${each.key}_.+", disk_key_name)) > 0
    }

    content {
      storage = storage_devices.value.id
    }
  }

  # Include at least one public SSH key
  login {
    user            = var.username
    keys            = var.ssh_public_keys
    create_password = false
  }
}

resource "upcloud_server" "worker" {
  for_each = {
    for name, machine in var.machines :
    name => machine
    if machine.node_type == "worker"
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
    ignore_changes = [storage_devices]
  }

  firewall  = var.firewall_enabled

  dynamic "storage_devices" {
    for_each = {
      for disk_key_name, disk in upcloud_storage.additional_disks :
        disk_key_name => disk
        # Only add the disk if it matches the node name in the start of its name
        if length(regexall("^${each.key}_.+", disk_key_name)) > 0
    }

    content {
      storage = storage_devices.value.id
    }
  }

  # Include at least one public SSH key
  login {
    user            = var.username
    keys            = var.ssh_public_keys
    create_password = false
  }
}

resource "upcloud_firewall_rules" "master" {
  for_each = upcloud_server.master
  server_id = each.value.id

  dynamic firewall_rule {
    for_each = var.master_allowed_remote_ips

    content {
      action                 = "accept"
      comment                = "Allow master API access from this network"
      destination_port_end   = "6443"
      destination_port_start = "6443"
      direction              = "in"
      family                 = "IPv4"
      protocol               = "tcp"
      source_address_end     = firewall_rule.value.end_address
      source_address_start   = firewall_rule.value.start_address
    }
  }

  dynamic firewall_rule {
    for_each = length(var.master_allowed_remote_ips) > 0 ? [1] : []

    content {
      action                 = "drop"
      comment                = "Deny master API access from other networks"
      destination_port_end   = "6443"
      destination_port_start = "6443"
      direction              = "in"
      family                 = "IPv4"
      protocol               = "tcp"
      source_address_end     = "255.255.255.255"
      source_address_start   = "0.0.0.0"
    }
  }

  dynamic firewall_rule {
    for_each = var.k8s_allowed_remote_ips

    content {
      action                 = "accept"
      comment                = "Allow SSH from this network"
      destination_port_end   = "22"
      destination_port_start = "22"
      direction              = "in"
      family                 = "IPv4"
      protocol               = "tcp"
      source_address_end     = firewall_rule.value.end_address
      source_address_start   = firewall_rule.value.start_address
    }
  }

  dynamic firewall_rule {
    for_each = length(var.k8s_allowed_remote_ips) > 0 ? [1] : []

    content {
      action                 = "drop"
      comment                = "Deny SSH from other networks"
      destination_port_end   = "22"
      destination_port_start = "22"
      direction              = "in"
      family                 = "IPv4"
      protocol               = "tcp"
      source_address_end     = "255.255.255.255"
      source_address_start   = "0.0.0.0"
    }
  }

  dynamic firewall_rule {
    for_each = var.master_allowed_ports

    content {
      action                 = "accept"
      comment                = "Allow access on this port"
      destination_port_end   = firewall_rule.value.port_range_max
      destination_port_start = firewall_rule.value.port_range_min
      direction              = "in"
      family                 = "IPv4"
      protocol               = firewall_rule.value.protocol
      source_address_end     = firewall_rule.value.end_address
      source_address_start   = firewall_rule.value.start_address
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["tcp", "udp"] : []

    content {
      action                 = "accept"
      comment                = "UpCloud DNS"
      source_port_end        = "53"
      source_port_start      = "53"
      direction              = "in"
      family                 = "IPv4"
      protocol               = firewall_rule.value
      source_address_end     = "94.237.40.9"
      source_address_start   = "94.237.40.9"
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["tcp", "udp"] : []

    content {
      action                 = "accept"
      comment                = "UpCloud DNS"
      source_port_end        = "53"
      source_port_start      = "53"
      direction              = "in"
      family                 = "IPv4"
      protocol               = firewall_rule.value
      source_address_end     = "94.237.127.9"
      source_address_start   = "94.237.127.9"
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["tcp", "udp"] : []

    content {
      action                 = "accept"
      comment                = "UpCloud DNS"
      source_port_end        = "53"
      source_port_start      = "53"
      direction              = "in"
      family                 = "IPv6"
      protocol               = firewall_rule.value
      source_address_end     = "2a04:3540:53::1"
      source_address_start   = "2a04:3540:53::1"
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["tcp", "udp"] : []

    content {
      action                 = "accept"
      comment                = "UpCloud DNS"
      source_port_end        = "53"
      source_port_start      = "53"
      direction              = "in"
      family                 = "IPv6"
      protocol               = firewall_rule.value
      source_address_end     = "2a04:3544:53::1"
      source_address_start   = "2a04:3544:53::1"
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["udp"] : []

    content {
      action                 = "accept"
      comment                = "NTP Port"
      source_port_end        = "123"
      source_port_start      = "123"
      direction              = "in"
      family                 = "IPv4"
      protocol               = firewall_rule.value
      source_address_end     = "255.255.255.255"
      source_address_start   = "0.0.0.0"
    }
  }

  dynamic firewall_rule {
    for_each = var.firewall_default_deny_in ? ["udp"] : []

    content {
      action                 = "accept"
      comment                = "NTP Port"
      source_port_end        = "123"
      source_port_start      = "123"
      direction              = "in"
      family                 = "IPv6"
      protocol               = firewall_rule.value
    }
  }

  firewall_rule {
    action    = var.firewall_default_deny_in ? "drop" : "accept"
    direction = "in"
  }

  firewall_rule {
    action    = var.firewall_default_deny_out ? "drop" : "accept"
    direction = "out"
  }
}

resource "upcloud_firewall_rules" "k8s" {
  for_each = upcloud_server.worker
  server_id = each.value.id

  dynamic firewall_rule {
    for_each = var.k8s_allowed_remote_ips

    content {
      action                 = "accept"
      comment                = "Allow SSH from this network"
      destination_port_end   = "22"
      destination_port_start = "22"
      direction              = "in"
      family                 = "IPv4"
      protocol               = "tcp"
      source_address_end     = firewall_rule.value.end_address
      source_address_start   = firewall_rule.value.start_address
    }
  }

  dynamic firewall_rule {
    for_each = length(var.k8s_allowed_remote_ips) > 0 ? [1] : []

    content {
      action             