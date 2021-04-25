# Calico

Check if the calico-node container is running

```ShellSession
docker ps | grep calico
```

The **calicoctl.sh** is wrap script with configured access credentials for command calicoctl allows to check the status of the network workloads.

* Check the status of Calico nodes

```ShellSession
calicoctl.sh node status
```

* Show the configured network subnet for containers

```ShellSession
calicoctl.sh get ippool -o wide
```

* Show the workloads (ip addresses of containers and their location)

```ShellSession
calicoctl.sh get workloadEndpoint -o wide
```

and

```ShellSession
calicoctl.sh get hostEndpoint -o wide
```

## Configuration

### Optional : Define datastore type

The default datastore, Kubernetes API datastore is recommended for on-premises deployments, and supports only Kubernetes workloads; etcd is the best datastore for hybrid deployments.

Allowed values are `kdd` (default) and `etcd`.

Note: using kdd and more than 50 nodes, consider using the `typha` daemon to provide scaling.

To re-define you need to edit the inventory and add a group variable `calico_datastore`

```yml
calico_datastore: kdd
```

### Optional : Define network backend

In some cases you may want to define Calico network backend. Allowed values are `bird`, `vxlan` or `none`. `vxlan` is the default value.

To re-define you need to edit the inventory and add a group variable `calico_network_backend`

```yml
calico_network_backend: none
```

### Optional : Define the default pool CIDRs

By default, `kube_pods_subnet` is used as the IP range CIDR for the default IP Pool, and `kube_pods_subnet_ipv6` for IPv6.
In some cases you may want to add several pools and not have them considered by Kubernetes as external (which means that they must be within or equal to the range defined in `kube_pods_subnet` and `kube_pods_subnet_ipv6` ), it starts with the default IP Pools of which IP range CIDRs can by defined in group_vars (k8s_cluster/k8s-net-calico.yml):

```ShellSession
calico_pool_cidr: 10.233.64.0/20
calico_pool_cidr_ipv6: fd85:ee78:d8a6:8607::1:0000/112
```

### Optional : BGP Peering with border routers

In some cases you may want to route the pods subnet and so NAT is not needed on the nodes.
For instance if you have a cluster spread on different locations and you want your pods to talk each other no matter where they are located.
The following variables need to be set as follow:

```yml
peer_with_router: true  # enable the peering with the datacenter's border router (default value: false).
nat_outgoing: false  # (optional) NAT outgoing (default value: true).
```

And you'll need to edit the inventory and add a hostvar `local_as` by node.

```ShellSession
node1 ansible_ssh_host=95.54.0.12 local_as=xxxxxx
```

### Optional : Defining BGP peers

Peers can be defined using the `peers` variable (see docs/calico_peer_example examples).
In order to define global peers, the `peers` variable can be defined in group_vars with the "scope" attribute of each global peer set to "global".
In order to define peers on a per node basis, the `peers` variable must be defined in hostvars.
NB: Ansible's `hash_behaviour` is by default set to "replace", thus defining both global and per node peers would end up with having only per node peers. If having both global and per node peers defined was meant to happen, global peers would have to be defined in hostvars for each host (as well as per node peers)

Since calico 3.4, Calico supports advertising Kubernetes service cluster IPs over BGP, just as it advertises pod IPs.
This can be enabled by setting the following variable as follow in group_vars (k8s_cluster/k8s-net-calico.yml)

```yml
calico_advertise_cluster_ips: true
```

Since calico 3.10, Calico supports advertising Kubernetes service ExternalIPs over BGP in addition to cluster IPs advertising.
This can be enabled by setting the following variable in group_vars (