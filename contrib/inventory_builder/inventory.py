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

        # If the user wa