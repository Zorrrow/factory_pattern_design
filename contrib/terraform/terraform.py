#!/usr/bin/env python3
#
# Copyright 2015 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# original: https://github.com/CiscoCloud/terraform.py

"""\
Dynamic inventory for Terraform - finds all `.tfstate` files below the working
directory and generates an inventory based on them.
"""
import argparse
from collections import defaultdict
import random
from functools import wraps
import json
import os
import re

VERSION = '0.4.0pre'


def tfstates(root=None):
    root = root or os.getcwd()
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if os.path.splitext(name)[-1] == '.tfstate':
                yield os.path.join(dirpath, name)

def convert_to_v3_structure(attributes, prefix=''):
    """ Convert the attributes from v4 to v3
    Receives a dict and return a dictionary """
    result = {}
    if isinstance(attributes, str):
        # In the case when we receive a string (e.g. values for security_groups)
        return {'{}{}'.format(prefix, random.randint(1,10**10)): attributes}
    for key, value in attributes.items():
        if isinstance(value, list):
            if len(value):
                result['{}{}.#'.format(prefix, key, hash)] = len(value)
            for i, v in enumerate(value):
                result.update(convert_to_v3_structure(v, '{}{}.{}.'.format(prefix, key, i)))
        elif isinstance(value, dict):
            result['{}{}.%'.format(prefix, key)] = len(value)
            for k, v in value.items():
                result['{}{}.{}'.format(prefix, key, k)] = v
        else:
            result['{}{}'.format(prefix, key)] = value
    return result

def iterresources(filenames):
    for filename in filenames:
        with open(filename, 'r') as json_file:
            state = json.load(json_file)
            tf_version = state['version']
            if tf_version == 3:
                for module in state['modules']:
                    name = module['path'][-1]
                    for key, resource in module['resources'].items():
                        yield name, key, resource
            elif tf_version == 4:
                # In version 4 the structure changes so we need to iterate
                # each instance inside the resource branch.
                for resource in state['resources']:
                    name = resource['provider'].split('.')[-1]
                    for instance in resource['instances']:
                        key = "{}.{}".format(resource['type'], resource['name'])
                        if 'index_key' in instance:
                           key = "{}.{}".format(key, instance['index_key'])
                        data = {}
                        data['type'] = resource['type']
                        data['provider'] = resource['provider']
                        data['depends_on'] = instance.get('depends_on', [])
                        data['primary'] = {'attributes': convert_to_v3_structure(instance['attributes'])}
                        if 'id' in instance['attributes']:
                           data['primary']['id'] = instance['attributes']['id']
                        data['primary']['meta'] = instance['attributes'].get('meta',{})
                        yield name, key, data
            else:
                raise KeyError('tfstate version %d not supported' % tf_version)


## READ RESOURCES
PARSERS = {}


def _clean_dc(dcname):
    # Consul DCs are strictly alphanumeric with underscores and hyphens -
    # ensure that the consul_dc attribute meets these requirements.
    return re.sub('[^\w_\-]', '-', dcname)


def iterhosts(resources):
    '''yield host tuples of (name, attributes, groups)'''
    for module_name, key, resource in resources:
        resource_type, name = key.split('.', 1)
        try:
            parser = PARSERS[resource_type]
        except KeyError:
            continue

        yield parser(resource, module_name)


def iterips(resources):
    '''yield ip tuples of (port_id, ip)'''
    for module_name, key, resource in resources:
        resource_type, name = key.split('.', 1)
        if resource_type == 'openstack_networking_floatingip_associate_v2':
            yield openstack_floating_ips(resource)


def parses(prefix):
    def inner(func):
        PARSERS[prefix] = func
        return func

    return inner


def calculate_mantl_vars(func):
    """calculate Mantl vars"""

    @wraps(func)
    def inner(*args, **kwargs):
        name, attrs, groups = func(*args, **kwargs)

        # attrs
        if attrs.get('role', '') == 'control':
            attrs['consul_is_server'] = True
        else:
            attrs['consul_is_server'] = False

        # groups
        if attrs.get('publicly_routable', False):
            groups.append('publicly_routable')

        return name, attrs, groups

    return inner


def _parse_prefix(source, prefix, sep='.'):
    for compkey, value in list(source.items()):
        try:
            curprefix, rest = compkey.split(sep, 1)
        except ValueError:
            continue

        if curprefix != prefix or rest == '#':
            continue

        yield rest, value


def parse_attr_list(source, prefix, sep='.'):
    attrs = defaultdict(dict)
    for compkey, value in _parse_prefix(source, prefix, sep):
        idx, key = compkey.split(sep, 1)
        attrs[idx][key] = value

    return list(attrs.values())


def parse_dict(source, prefix, sep='.'):
    return dict(_parse_prefix(source, prefix, sep))


def parse_list(source, prefix, sep='.'):
    return [value for _, value in _parse_prefix(source, prefix, sep)]


def parse_bool(string_form):
    if type(string_form) is bool:
        return string_form

    token = string_form.lower()[0]

    if token == 't':
        return True
    elif token == 'f':
        return False
    else:
        raise ValueError('could not convert %r to a bool' % string_form)

def sanitize_groups(groups):
    _groups = []
    chars_to_replace = ['+', '-', '=', '.', '/', ' ']
    for i in groups:
        _i = i
        for char in chars_to_replace:
            _i = _i.replace(char, '_')
        _groups.append(_i)
    groups.clear()
    groups.extend(_groups)

@parses('equinix_metal_device')
def equinix_metal_device(resource, tfvars=None):
    raw_attrs = resource['primary']['attributes']
    name = raw_attrs['hostname']
    groups = []

    attrs = {
        'id': raw_attrs['id'],
        'facilities': parse_list(raw_attrs, 'facilities'),
        'hostname': raw_attrs['hostname'],
        'operating_system': raw_attrs['operating_system'],
        'locked': parse_bool(raw_attrs['locked']),
        'tags': parse_list(raw_attrs, 'tags'),
        'plan': raw_attrs['plan'],
        'project_id': raw_attrs['project_id'],
        'state': raw_attrs['state'],
        # ansible
        'ansible_host': raw_attrs['network.0.address'],
        'ansible_ssh_user': 'root',  # Use root by default in metal
        # generic
        'ipv4_address': raw_attrs['network.0.address'],
        'public_ipv4': raw_attrs['network.0.address'],
        'ipv6_address': raw_attrs['network.1.address'],
        'public_ipv6': raw_attrs['network.1.address'],
        'private_ipv4': raw_attrs['network.2.address'],
        'provider': 'equinix',
    }

    if raw_attrs['operating_system'] == 'flatcar_stable':
        # For Flatcar set the ssh_user to core
        attrs.update({'ansible_ssh_user': 'core'})

    # add groups based on attrs
    groups.append('equinix_metal_operating_system_%s' % attrs['operating_system'])
    groups.append('equinix_metal_locked_%s' % attrs['locked'])
    groups.append('equinix_metal_state_%s' % attrs['state'])
    groups.append('equinix_metal_plan_%s' % attrs['plan'])

    # groups specific to kubespray
    groups = groups + attrs['tags']
    sanitize_groups(groups)

    return name, attrs, groups


def openstack_floating_ips(resource):
    raw_attrs = resource['primary']['attributes']
    attrs = {
        'ip': raw_attrs['floating_ip'],
        'port_id': raw_attrs['port_id'],
    }
    return attrs

def openstack_floating_ips(resource):
    raw_attrs = resource['primary']['attributes']
    return raw_attrs['port_id'], raw_attrs['floating_ip']

@parses('openstack_compute_instance_v2')
@calculate_mantl_vars
def openstack_host(resource, module_name):
    raw_attrs = resource['primary']['attributes']
    name = raw_attrs['name']
    groups = []

    attrs = {
        'access_ip_v4': raw_attrs['access_ip_v4'],
        'access_ip_v6': raw_attrs['access_ip_v6'],
        'access_ip': raw_attrs['access_ip_v4'],
        'ip': raw_attrs['network.0.fixed_ip_v4'],
        'flavor': parse_dict(raw_attrs, 'flavor',
                             sep='_'),
        'id': raw_attrs['id'],
        'image': parse_dict(raw_attrs, 'image',
                            sep='_'),
        'key_pair': raw_attrs['key_pair'],
        'metadata': parse_dict(raw_attrs, 'metadata'),
        'network': parse_attr_list(raw_attrs, 'network'),
        'region': raw_attrs.get('region', ''),
        'security_groups': parse_list(raw_attrs, 'security_groups'),
        # workaround for an OpenStack bug where hosts have a different domain
        # after they're restarted
        'host_domain': 'novalocal',
        'use_host_domain': True,
        # generic
      