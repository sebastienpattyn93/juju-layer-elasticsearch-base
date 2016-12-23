#!/usr/bin/env python3
# pylint: disable=c0111,c0103,c0301
import pwd
import grp
import os
import subprocess as sp

from subprocess import CalledProcessError
from jujubigdata import utils
from charms.reactive import (
    when,
    when_not,
    when_file_changed,
    set_state,
    remove_state
)
from charmhelpers.core.hookenv import (
    status_set,
    application_version_set,
    config,
    open_port
)
from charmhelpers.core.host import (
    service_running,
    service_start,
    service_restart
)
from charms.layer.elasticsearch_base import (#pylint: disable=E0611,E0401,C0412
    is_container,
    es_version
)

#@when('java.ready')
@when_not('elasticsearch.installed')
def install_elasticsearch():
    """Check for container, install elasticsearch
    """
    # Workaround for container installs is to set
    # ES_SKIP_SET_KERNEL_PARAMETERS if in container
    # so kernel files will not need to be modified on
    # elasticsearch install. See
    # https://github.com/elastic/elasticsearch/commit/32df032c5944326e351a7910a877d1992563f791
    if is_container():
        os.environ['ES_SKIP_SET_KERNEL_PARAMETERS'] = "true"
    sp.call(['apt', 'install', 'elasticsearch', '-y',
             '--allow-unauthenticated'], shell=False)
    set_state('elasticsearch.installed')

@when('elasticsearch.installed')
@when_not('elasticsearch.configured')
def configure_elasticsearch():
    conf = config()
    status_set('maintenance', 'Configuring elasticsearch')
    path = '/etc/elasticsearch/elasticsearch.yml'
    # check if Firewall has to be enabled
    init_fw()
    # change the default settings
    # might want to do this with a template in the future
    # or not in base layer but in specific charm
    utils.re_edit_in_place(path, {
        r'#cluster.name: my-application': 'cluster.name: {0}'.format(conf['cluster_name']),
    })
    utils.re_edit_in_place(path, {
        r'#network.host: 192.168.0.1': 'network.host: ["_site_", "_local_"]',
    })
    # ownership needs to be changed to elasticsearch
    uid = pwd.getpwnam("root").pw_uid
    gid = grp.getgrnam("elasticsearch").gr_gid
    os.chown(path, uid, gid)
    set_state('elasticsearch.configured')

@when('elasticsearch.configured')
@when_file_changed('/etc/elasticsearch/elasticsearch.yml')
def restart():
    try:
        status_set('maintenance', 'Restarting elasticsearch')
        service_restart('elasticsearch')
        set_state('elasticsearch.ready')
        status_set('active', 'Ready')
    except CalledProcessError:
        status_set('error', 'Could not restart elasticsearch')

@when('elasticsearch.ready')
@when_not('elasticsearch.running')
def ensure_elasticsearch_running():
    """Ensure elasticsearch is started
    """

    # If elasticsearch isn't running start it
    if not service_running('elasticsearch'):
        service_start('elasticsearch')
    # If elasticsearch starts, were g2g, else block
    if service_running('elasticsearch'):
        set_state('elasticsearch.running')
    else:
        # If elasticsearch wont start, set blocked
        set_state('elasticsearch.problems')


@when('elasticsearch.ready', 'elasticsearch.running')
@when_not('elasticsearch.version.set')
def get_set_elasticsearch_version():
    """Wait until we have the version to confirm
    elasticsearch has started
    """

    status_set('maintenance', 'Waiting for Elasticsearch to start')
    application_version_set(es_version())
    open_port(9200)
    status_set('active', 'Elasticsearch started')
    set_state('elasticsearch.version.set')


@when('elasticsearch.version.set')
@when_not('elasticsearch.base.available')
def set_elasticsearch_base_available():
    """Set active status, and 'elasticsearch.base.available'
    state
    """
    status_set('active', 'Elasticsearch base available')
    set_state('elasticsearch.base.available')


@when('elasticsearch.problems')
def blocked_due_to_problems():
    """Set blocked status if we encounter issues
    """
    status_set('blocked',
               "There are problems with elasticsearch, please debug")

######################
# Relation functions #
######################

@when('client.connected', 'elasticsearch.configured')
def connect_to_client(connected_clients):
    conf = config()
    cluster_name = conf['cluster-name']
    port = conf['port']
    connected_clients.configure(port, cluster_name)
    clients = connected_clients.list_connected_clients_data
    for c in clients:
        add_fw_exception(c)

@when('client.broken')
def remove_client(broken_clients):
    #
    clients = broken_clients.list_connected_clients_data
    for c in clients:
        if c is not None:
            rm_fw_exception(c)
    remove_state('client.broken')

######################
# Firewall Functions #
######################

def init_fw():
    conf = config()
    #this value has te be changed to set ufw rules
    utils.re_edit_in_place('/etc/default/ufw', {
        r'IPV6=yes': 'IPV6=no',
    })
    if conf['firewall_enabled']:
        sp.check_call(['ufw', 'allow', '22'])
        sp.check_output(['ufw', 'enable'], input='y\n', universal_newlines=True)
    else:
        sp.check_output(['ufw', 'disable'])

def add_fw_exception(host_ip):
    sp.check_call([
        'ufw', 'allow', 'proto', 'tcp', 'from', host_ip,
        'to', 'any', 'port', '9200'])

def  rm_fw_exception(host_ip):
    sp.check_call([
        'ufw', 'delete', 'allow', 'proto', 'tcp', 'from', host_ip,
        'to', 'any', 'port', '9200'])
