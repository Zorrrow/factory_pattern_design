
variable "number_of_k8s_masters" {}

variable "number_of_k8s_masters_no_etcd" {}

variable "number_of_k8s_nodes" {}

variable "floatingip_pool" {}

variable "number_of_bastions" {}

variable "external_net" {}

variable "network_name" {}

variable "router_id" {
  default = ""
}

variable "k8s_masters" {}

variable "k8s_nodes" {}

variable "k8s_master_fips" {}

variable "bastion_fips" {}

variable "router_internal_port_id" {}