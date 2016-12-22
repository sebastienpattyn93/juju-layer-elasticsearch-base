import os, subprocess

from charms.reactive import when, when_not, set_state

from charmhelpers.core.hookenv import status_set
from charmhelpers.core.host import (
    service_running,
    service_start
)

from charms.layer.elasticsearch_base import is_container


@when('java.ready')
@when_not('elasticsearch.installed')
def install_elasticsearch(java):
    """Check for container, install elasticsearch
    """

    # Workaround for container installs is to set 
    # ES_SKIP_SET_KERNEL_PARAMETERS if in container
    # so kernel files will not need to be modified on
    # elasticsearch install. See
    # https://github.com/elastic/elasticsearch/commit/32df032c5944326e351a7910a877d1992563f791
    if is_container():
        os.environ['ES_SKIP_SET_KERNEL_PARAMETERS'] = "true"
    subprocess.call(['apt', 'install', 'elasticsearch', '-y',
                     '--allow-unauthenticated'], shell=False)
    set_state('elasticsearch.installed')


@when('elasticsearch.installed')
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


@when('elasticsearch.installed', 'elasticsearch.running')
def set_ready_status():
    """Set ready status
    """
    status_set('active', 'Elasticsearch ready')


@when('elasticsearch.problems')
def blocked_due_to_problems():
    """Set blocked status if we encounter issues
    """
    status_set('blocked',
               "There are problems with elasticsearch, please debug")
