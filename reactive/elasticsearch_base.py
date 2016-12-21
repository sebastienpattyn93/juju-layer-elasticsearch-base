from charms.reactive import when, when_not, set_state


@when('apt.installed.elasticsearch')
@when_not('elasticsearch.installed')
def set_es_installed_state():
    set_state('elasticsearch.installed')
