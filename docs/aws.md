# AWS

To deploy kubespray on [AWS](https://aws.amazon.com/) uncomment the `cloud_provider` option in `group_vars/all.yml` and set it to `'aws'`. Refer to the [Kubespray Configuration](#kubespray-configuration) for customizing the provider.

Prior to creating your instances, you **must** ensure that you have created IAM roles and policies for both "kubernetes-master" and "kubernetes-node". You can find the IAM policies [here](https://github.com/kubernetes-sigs/kubespray/tree/master/contrib/aws_iam/). See the [IAM Documentation](https://aws.amazon.com/documentation/iam/) if guidance is needed on how to set these up. When you bring your instances online, associate them with the respective IAM role. Nodes that are only to be used for Etcd do not need a role.

You would also need to tag the resources in your VPC accordingly for the aws provider to utilize them. Tag the subnets, route tables and all instances that kubernetes will be run on with key `kubernetes.io/cluster/$cluster_name` (`$cluster_name` must be a unique identifier for the cluster). Tag the subnets that must be targeted by external ELBs with the key `kubernetes.io/role/elb` and 