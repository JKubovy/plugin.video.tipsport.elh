# coding=utf-8
import re
import xbmc


def log(message):
    xbmc.log('|plugin.video.tipsport.elh|\t{0}'.format(message))


def get_session_id_from_page(page_text):
    regex = '\'sessionId\': \'(.*?)\','
    session_id = re.search(regex, page_text)
    if session_id:
        return session_id.group(1)
    log('sessionId not found')
    return None
