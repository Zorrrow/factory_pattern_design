#!/usr/bin/env python3
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Usage: inventory.py ip1 [ip2 ...]
# Examples: inventory.py 10.10.1.3 10.10.1.4 10.10.1.5
#
# Advanced usage:
# Add another host after initial creation: inventory.py 10.10.1.5
# Add range of hosts: inventory.py 10.10.1.3-10.10.1.5
# Add hosts with different ip and access ip:
# inventory.py 10.0.0.1,192.168.10.1 10.0.0.2,192.168.10.2 10.0.0.3,192.168.1.3
# Add hosts with a specific hostname, ip, and optional access ip:
# inventory.py first,10.0.0.1,192.168.10.1 second,10.0.0.2 last,10.0.0.3
# Delete a host: inventory.py -10.10.1.3
# Delete a host by id: inventory.py -node1
#
# Load a YAML or JSON file with inventory data: inventory.py load hosts.yaml
# YAML file should be in the following format:
#    group1:
#      host1:
#        ip: X.X.X.X
#        var: val
#    group2:
#      host2:
#        ip: X.X.X.X

from collections import OrderedDict
from ipaddress import ip_address
from ruamel.yaml import YAML

import os
import re
import subprocess
import sys

ROLES = ['all', 'kube_control_plane', 'kube_node', 'etcd', 'k8s_cluster',
         'calico_rr']
PROTECTED_NAMES = ROLES
AVAILABLE_COMMANDS = ['help', 'print_cfg', 'print_ips', 'print_hostnames',
                      'load', 'add']
_boolean_states = {'1': True, 'yes': True, 'true': True, 'on': True,
                   '0': False, 'no': False, 'false': False, 'off': False}
yaml = YAML()
yaml.Representer.add_representer(OrderedDict, yaml.Representer.represent_dict)


def get_var_as_bool(name, default):
    value = os.environ.get(name, '')
    return _boolean_states.get(value.lower(), default)

# Configurable as shell vars start


CONFIG_FILE = os.environ.get("CONFIG_FILE", "./inventory/sample/hosts.yaml")
# Remove the reference of KUBE_MASTERS after some deprecation cycles.
KUBE_CONTROL_HOSTS = int(os.environ.get("KUBE_CONTROL_HOSTS",
                         os.environ.get("KUBE_MASTERS", 2)))
# Reconfigures cluster distribution at scale
SCALE_THRESHOLD = int(os.environ.get("SCALE_THRESHOLD", 50))
MASSIVE_SCALE_THRESHOLD = int(os.environ.get("MASSIVE_SCALE_THRESHOLD", 200))

DEBUG = get_var_as_bool("DEBUG", True)
HOST_PREFIX = os.environ.get("HOST_PREFIX", "node")
USE_REAL_HOSTNAME = get_var_as_bool("USE_REAL_HOSTNAME", False)

# Configurable as shell vars end


class KubesprayInventory(object):

    def __init__(self, changed_hosts=None, config_file=None):
        self.config_file = config_file
        self.yaml_config = {}
        loadPreviousConfig = False
        printHostnames = False
        # See whether there are any commands to process
        if changed_hosts and changed_hosts[0] in AVAILABLE_COMMANDS:
            if changed_hosts[0] == "add":
                loadPreviousConfig = True
                changed_hosts = changed_hosts[1:]
            elif changed_hosts[0] == "print_hostnames":
                loadPreviousConfig = True
                printHostnames = True
            else:
                self.parse_command(changed_hosts[0], changed_hosts[1:])
                sys.exit(0)

        # If the user wants to remove a node, we need to load the config anyway
        if changed_hosts and changed_hosts[0][0] == "-":
            loadPreviousConfig = True

        if self.config_file and loadPreviousConfig:  # Load previous YAML file
            try:
                self.hosts_file = open(config_file, 'r')
                self.yaml_config = yaml.load(self.hosts_file)
            except OSError as e:
                # I am assuming we are catching "cannot open file" exceptions
                print(e)
                sys.exit(1)

        if printHostnames:
            self.print_hostnames()
            sys.exit(0)

        self.ensure_required_groups(ROLES)

        if changed_hosts:
            changed_hosts = self.range2ips(changed_hosts)
            self.hosts = self.build_hostnames(changed_hosts,
                                              loadPreviousConfig)
            self.purge_invalid_hosts(self.hosts.keys(), PROTECTED_NAMES)
            self.set_all(self.hosts)
            self.set_k8s_cluster()
            etcd_hosts_count = 3 if len(self.hosts.keys()) >= 3 else 1
            self.set_etcd(list(self.hosts.keys())[:etcd_hosts_count])
            if len(self.hosts) >= SCALE_THRESHOLD:
                self.set_kube_control_plane(list(self.hosts.keys())[
                    etcd_hosts_count:(etcd_hosts_count + KUBE_CONTROL_HOSTS)])
            else:
                self.set_kube_control_plane(
                  list(self.hosts.keys())[:KUBE_CONTROL_HOSTS])
            self.set_kube_node(self.hosts.keys())
            if len(self.hosts) >= SCALE_THRESHOLD:
                self.set_calico_rr(list(self.hosts.keys())[:etcd_hosts_count])
        else:  # Show help if no options
            self.show_help()
            sys.exit(0)

        self.write_config(self.config_file)

    def write_config(self, config_file):
        if config_file:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.yaml_config, f)

        else:
            print("WARNING: Unable to save config. Make sure you set "
                  "CONFIG_FILE env var.")

    def debug(self, msg):
        if DEBUG:
            print("DEBUG: {0}".format(msg))

    def get_ip_from_opts(self, optstring):
        if 'ip' in optstring:
            return optstring['ip']
        else:
            raise ValueError("IP parameter not found in options")

    def ensure_required_groups(self, groups):
        for group in groups:
            if group == 'all':
                self.debug("Adding group {0}".format(group))
                if group not in self.yaml_config:
                    all_dict = OrderedDict([('hosts', OrderedDict({})),
                                            ('children', OrderedDict({}))])
                    self.yaml_config = {'all': all_dict}
            else:
                self.debug("Adding group {0}".format(group))
                if group not in self.yaml_config['all']['children']:
                    self.yaml_config['all']['children'][group] = {'hosts': {}}

    def get_host_id(self, host):
        '''Returns integer host ID (without padding) from a given hostname.'''
        try:
            short_hostname = host.split('.')[0]
            return int(re.findall("\\d+$", short_hostname)[-1])
        except IndexError:
            raise ValueError("Host name must end in an integer")

    # Keeps already specified hosts,
    # and adds or removes the hosts provided as an argument
    def build_hostnames(self, changed_hosts, loadPreviousConfig=False):
        existing_hosts = OrderedDict()
        highest_host_id = 0
        # Load already existing hosts from the YAML
        if loadPreviousConfig:
            try:
                for host in self.yaml_config['all']['hosts']:
                    # Read configuration of an existing host
                    hostConfig = self.yaml_config['all']['hosts'][host]
                    existing_hosts[host] = hostConfig
                    # If the existing host seems
                    # to have been created automatically, detect its ID
                    if host.startswith(HOST_PREFIX):
                        host_id = self.get_host_id(host)
                        if host_id > highest_host_id:
                            highest_host_id = host_id
            except Exception as e:
                # I am assuming we are catching automatically
                # created hosts without IDs
                print(e)
                sys.exit(1)

        # FIXME(mattymo): Fix condition where delete then add reuses highest id
        next_host_id = highest_host_id + 1
        next_host = ""

        all_hosts = existing_hosts.copy()
        for host in changed_hosts:
            # Delete the host from config the hostname/IP has a "-" prefix
            if host[0] == "-":
                realhost = host[1:]
                if self.exists_hostname(all_hosts, realhost):
                    self.debug("Marked {0} for deletion.".format(realhost))
                    all_hosts.pop(realhost)
                elif self.exists_ip(all_hosts, realhost):
                    self.debug("Marked {0} for deletion.".format(realhost))
                    self.delete_host_by_ip(all_hosts, realhost)
            # Host/Argument starts with a digit,
            # then we assume its an IP address
            elif host[0].isdigit():
                if ',' in host:
                    ip, access_ip = host.split(',')
                else:
                    ip = host
                    access_ip = host
                if self.exists_hostname(all_hosts, host):
                    self.debug("Skipping existing host {0}.".format(host))
                    continue
                elif self.exists_ip(all_hosts, ip):
                    self.debug("Skipping existing host {0}.".format(ip))
                    continue

                if USE_REAL_HOSTNAME:
                    cmd = ("ssh -oStrictHostKeyChecking=no "
                           + access_ip + " 'hostname -s'")
                    next_host = subprocess.check_output(cmd, shell=True)
                    next_host = next_host.strip().decode('ascii')
                else:
                    # Generates a hostname because we have only an IP address
                    next_host = "{0}{1}".format(HOST_PREFIX, next_host_id)
                    next_host_id += 1
                # Uses automatically generated node name
                # in case we dont provide it.
                all_hosts[next_host] = {'ansible_host': access_ip,
                                        'ip': ip,
                                        'access_ip': access_ip}
            # Host/Argument starts with a letter, then we assume its a hostname
            elif host[0].isalpha():
                if ',' in host:
                    try:
                        hostname, ip, access_ip = host.split(',')
                    except Exception:
                        hostname, ip = host.split(',')
                        access_ip = ip
                if self.exists_hostname(all_hosts, host):
                    self.debug("Skipping existing host {0}.".format(host))
                    continue
                elif self.exists_ip(all_hosts, ip):
                    self.debug("Skipping existing host {0}.".format(ip))
                    continue
                all_hosts[hostname] = {'ansible_host': access_ip,
                                       'ip': ip,
                                       'access_ip': access_ip}
        return all_hosts

    # Expand IP ranges into individual addresses
    def range2ips(self, hosts):
        reworked_hosts = []

        def ips(start_address, end_address):
            try:
                # Python 3.x
                start = int(ip_address(start_address))
                end = int(ip_address(end_address))
            except Exception:
                # Python 2.7
                start = int(ip_address(str(start_address)))
                end = int(ip_address(str(end_address)))
            return [ip_address(ip).exploded for ip in range(start, end + 1)]

        for host in hosts:
            if '-' in host and not (host.startswith('-') or host[0].isalpha()):
                start, end = host.strip().split('-')
                try:
      