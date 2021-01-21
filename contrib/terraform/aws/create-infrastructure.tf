terraform {
  required_version = ">= 0.12.0"
}

provider "aws" {
  access_key = var.AWS_ACCESS_KEY_ID
  secret_key = var.AWS_SECRET_ACCESS_KEY
  region     = var.AWS_DEFAULT_REGION
}

data "aws_availability_zones" "available" {}

/*
* Calling modules who create the initial AWS VPC / AWS ELB
* and AWS IAM Roles for Kubernetes Deployment
*/

module "aws-vpc" {
  source = "./modules/vpc"

  aws_cluster_name         = var.aws_cluster_name
  aws_vpc_cidr_block       = var.aws_vpc_cidr_block
  aws_avail_zones          = data.aws_availability_zones.available.names
  aws_cidr_subnets_private = var.aws_cidr_subnets_private
  aws_cidr_subnets_public  = var.aws_cidr_subnets_public
  default_tags             = var.default_tags
}

module "aws-nlb" {
  source = "./modules/nlb"

  aws_cluster_name      = var.aws_cluster_name
  aws_vpc_id            = module.aws-vpc.aws_vpc_id
  aws_avail_zones       = data.aws_availability_zones.available.names
  aws_subnet_ids_public = module.aws-vpc.aws_subnet_ids_public
  aws_nlb_api_port      = var.aws_nlb_api_port
  k8s_secure_api_port   = var.k8s_secure_api_port
  default_tags          = var.default_tags
}

module "aws-iam" {
  source = "./modules/iam"

  aws_cluster_name = var.aws_cluster_name
}

/*
* Create Bastion Instances in AWS
*
*/

resource "aws_instance" "bastion-server" {
  ami                         = data.aws_ami.distro.id
  instance_type               = var.aws_bastion_size
  count                       = var.aws_bastion_num
  associate_public_ip_address = true
  subnet_id                   = ele