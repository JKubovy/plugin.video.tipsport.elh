# coding=utf-8
import re
from xbmc import log as log_fce


def log(message):
    log_fce('|plugin.video.tipsport.elh|\t{0}'.format(message))


def get_session_id_from_page(page_text):
    regex = '\'sessionId\': \'(.*?)\','
    session_id = re.search(regex, page_text)
    if session_id:
        return session_id.group(1)
    log('sessionId not found')
    return None
