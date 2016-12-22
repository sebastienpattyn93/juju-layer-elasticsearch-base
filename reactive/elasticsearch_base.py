import os
import subprocess as sp

from charms.reactive import when, when_not, set_state

from charmhelpers.core.hookenv import (
    status_set,
    application_version_set
)
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
    sp.call(['apt', 'install', 'elasticsearch', '-y',
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
@when_not('elasticsearch.version.set')
def get_set_elasticsearch_version():
    """Curl to localhost to get version
    (possibly there is a bettter way)

    Once we can curl localhost, we also know elasticsearch
    is functioning correctly.
    """
    # Poor mans hack here, we will have to look at a better way to
    # get the version
    es_curl_data = sp.check_output(["curl", "http://localhost:9200"])
    es_vers_str = es_curl_data.strip().decode()
    json_acceptable_data = es_vers_str.replace("\n","").replace("'","\"")
    es_version = json.loads(json_acceptable_data)['version']['number']
    application_version_set(es_version)
    set_state('elasticsearch.version.set')


@when('elasticsearch.version.set')
@when_not('elasticsearch.base.available')
def set_elasticsearch_base_available():
    """Set ready status, and 'elasticsearch.base.available'
    state
    """
    status_set('active', 'Elasticsearch ready')
    set_state('elasticsearch.base.available')


@when('elasticsearch.problems')
def blocked_due_to_problems():
    """Set blocked status if we encounter issues
    """
    status_set('blocked',
               "There are problems with elasticsearch, please debug")
