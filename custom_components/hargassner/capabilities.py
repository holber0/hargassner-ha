"""Capabilities and validation shared by boiler and buffer controls."""
from urllib.parse import urlsplit

PROGRAMS = ('PROGRAM_OFF', 'PROGRAM_AUTOMATIC', 'PROGRAM_BOILER', 'PROGRAM_STOP_FIRING')


def enabled_resource(item):
    """Accept only API-advertised, enabled resources on the Hargassner origin."""
    if not isinstance(item, dict):
        return None
    if item.get('disabled') not in (None, False, 0) or item.get('read_only') not in (None, False, 0):
        return None
    resource = item.get('resource')
    if not isinstance(resource, str) or not resource:
        return None
    parsed = urlsplit(resource)
    if parsed.username or parsed.password or parsed.fragment:
        return None
    if parsed.scheme or parsed.netloc:
        if parsed.scheme != 'https' or parsed.netloc != 'web.hargassner.at':
            return None
    elif not resource.startswith('/') or resource.startswith('//'):
        return None
    return resource


def cloud_ready(coordinator):
    return bool(coordinator.last_update_success and coordinator.data and coordinator.data.get('_online') is True)


def allowed_programs(parameter):
    if not isinstance(parameter, dict) or not isinstance(parameter.get('options'), list):
        return []
    return [option for option in parameter['options'] if isinstance(option, str) and option in PROGRAMS]


def active_bool(value):
    if value is True or value == 1:
        return True
    if value is False or value == 0:
        return False
    return None
