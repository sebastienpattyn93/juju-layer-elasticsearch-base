import os, subprocess

from charms.reactive import when, when_not, set_state

from charmhelpers.core.hookenv import status_set
from charmhelpers.core.host import (
    service_restart,
    service_running,
    service_start
)

from charms.layer.elasticsearch_base import is_container


@when('java.ready')
@when_not('elasticsearch.installed')
def install_elasticsearch(java):
    """Check for container, install elasticsearch
    """

    if is_container():
        os.environ['ES_SKIP_SET_KERNEL_PARAMETERS'] = "true"
    subprocess.call(['apt', 'install', 'elasticsearch', '-y',
                     '--allow-unauthenticated'], shell=False)
    set_state('elasticsearch.installed')


@when('elasticsearch.installed')
@when_not('elasticsearch.running')
def ensure_elasticsearch_running():
    """Ensure to start elasticsearch when elasticsearch
    is installed,but the 'elasticsearch.running' state is not set
    """

    if service_running('elasticsearch'):
        service_restart('elasticsearch')
    else:
        service_start('elasticsearch')
    set_state('elasticsearch.running')


@when('elasticsearch.installed', 'elasticsearch.running')
def set_ready_status():
    """Set ready status
    """
    status_set('active', 'Elasticsearch ready')
