provider "hcloud" {}

module "kubernetes" {
  source = "./modules/kubernetes-cl