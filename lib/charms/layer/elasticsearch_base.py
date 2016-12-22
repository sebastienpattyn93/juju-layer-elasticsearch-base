import json
import requests
from time import sleep
import subprocess as sp


def is_container():
    """Return True if system is running inside a container"""
    virt_type = sp.check_output('systemd-detect-virt').decode().strip()
    if virt_type == 'lxc':
        return True
    else:
        return False


def es_version():
    """Return elasticsearch version
    """

    # Poll until elasticsearch has started, otherwise the curl
    # to get the version will error out
    success = False
    while not success:
        try:
            status_code = requests.get('http://localhost:9200').status_code
            if status_code == 200:
                success = True
        except requests.exceptions.ConnectionError:
            sleep(1)
    es_curl_data = sp.check_output(["curl", "http://localhost:9200"])
    es_vers_str = es_curl_data.strip().decode()
    json_acceptable_data = es_vers_str.replace("\n","").replace("'","\"")
    version = json.loads(json_acceptable_data)['version']['number']
    return version
 
