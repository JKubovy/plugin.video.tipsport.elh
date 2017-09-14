import re
import sys
import xbmc
import xbmcgui
import xbmcplugin
import traceback
import requests
from resources.lib.tipsport_stream_generator import Tipsport
from resources.lib.tipsport_exceptions import *
from resources.lib.kodi_helper import KodiHelper


def send_crash_report(kodi_helper, exception):
    """Send crash log to google script to process it"""
    if not kodi_helper.send_crash_reports:
        return False
    try:
        session = requests.session()
        addon = kodi_helper.plugin_name
        version = kodi_helper.version
        data = traceback.format_exc(exception)
        params = {'addon': addon, 'version': version, 'data': data}
        url = 'https://script.google.com/macros/s/AKfycbyEXPShEN6O7Eounxf932MyzOHrsaRAcksU0LvEMcYRgXDRhqu-/exec'
        response = session.get(url, params=params, headers={"Content-type": "application/x-www-form-urlencoded"})
        response_text = re.search(r'userHtml\\x22:\\x22(.*?)\\x22', response.text)
        if response_text and response_text.group(1) == 'OK':
            return True
        else:
            return False
    except requests.ConnectionError, requests.ConnectTimeout:
        return False


def play_video(title, icon, link, media_type='Video'):
    """Start playing given video stream"""
    list_item = xbmcgui.ListItem(label=title, iconImage=icon, path=link)
    list_item.setInfo(type=media_type, infoLabels={"Title": title})
    list_item.setProperty('IsPlayable', 'true')
    xbmc.Player().play(item=link, listitem=list_item)


def show_localized_notification(kodi_helper, heading_string_id, message_string_id, icon=xbmcgui.NOTIFICATION_ERROR):
    """Show Kodi notification with given string ids"""
    xbmcgui.Dialog().notification(kodi_helper.get_local_string(heading_string_id),
                                  kodi_helper.get_local_string(message_string_id),
                                  icon)


def show_available_elh_matches(kodi_helper, tipsport):
    """Generate list of available elh matches in Kodi"""
    xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
    matches = tipsport.get_list_elh_matches()
    if len(matches) == 0:
        show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
    for match in matches:
        url = kodi_helper.build_url({'mode': 'play',
                                     'url': match.url,
                                     'name': match.name.encode('utf-8'),
                                     'start_time': match.start_time})
        if match.started:
            plot = '\n{text}: {score:<20}{status}'.format(text=kodi_helper.get_local_string(30003),
                                                          score=match.score,
                                                          status=match.status.encode('utf-8')
                                                          if xbmc.getLanguage(xbmc.ISO_639_1) == 'cs' else '')
        else:
            plot = '{text} {time}'.format(text=kodi_helper.get_local_string(30002), time=match.start_time)
        list_item = xbmcgui.ListItem(match.name, iconImage=kodi_helper.icon)
        list_item.setInfo(type='Video', infoLabels={'Plot': plot})
        xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item)
    xbmcplugin.endOfDirectory(kodi_helper.plugin_handle)


def main():
    kodi_helper = KodiHelper(plugin_handle=int(sys.argv[1]),
                             args=sys.argv[2][1:],
                             base_url=sys.argv[0])
    tipsport = Tipsport(kodi_helper.username, kodi_helper.password)
    mode = kodi_helper.get_arg('mode')
    try:
        if mode is None:
            show_available_elh_matches(kodi_helper, tipsport)
        elif mode == 'play':
            stream = tipsport.get_stream(kodi_helper.get_arg('url'))
            title = '{name} ({time})'.format(name=kodi_helper.get_arg('name'), time=kodi_helper.get_arg('start_time'))
            play_video(title, kodi_helper.icon, stream.get_rtmp_link())
        elif mode == 'check_login':
            tipsport.login()
            show_localized_notification(kodi_helper, 30000, 30001, xbmcgui.NOTIFICATION_INFO)
    except NoInternetConnectionsException:
        show_localized_notification(kodi_helper, 32000, 32001)
    except LoginFailedException:
        show_localized_notification(kodi_helper, 32000, 32002)
    except UnableGetStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32003)
    except UnableParseStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32004)
    except UnsupportedFormatStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32005)
    except UnableDetectScriptSessionIdException:
        show_localized_notification(kodi_helper, 32000, 32006)
    except UnableGetStreamNumberException:
        show_localized_notification(kodi_helper, 32000, 32007)
    except Exception as e:
        if send_crash_report(kodi_helper, e):
            show_localized_notification(kodi_helper, 32000, 32009)
        else:
            show_localized_notification(kodi_helper, 32000, 32008)


if __name__ == "__main__":
    main()
