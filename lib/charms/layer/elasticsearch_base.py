from subprocess import check_output


def is_container():
    """Return True if system is running inside a container"""
    virt_type = check_output('systemd-detect-virt').decode().strip()
    if virt_type == 'lxc':
        return True
    else:
        return False
