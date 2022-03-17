# coding=utf-8
import platform
from xbmc import log as log_fce


def log(message):
    log_fce('|plugin.video.tipsport.elh|\t{0}'.format(message))


def get_host_info():
    try:
        return {
            'Host': {
                'System': platform.system(),
                'Node': platform.node(),
                'Release': platform.release(),
                'Version': platform.version(),
                'Machine': platform.machine(),
                'Processor': platform.processor()
            },
            'Python': {
                'Implementation': platform.python_implementation(),
                'Version': platform.python_version(),
                'Compiler': platform.python_compiler()
            }
        }
    except Exception:
        return None
