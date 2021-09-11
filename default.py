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
from resources.lib.mem_storage import MemStorage
from resources.lib.utils import log


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
    except (requests.ConnectionError, requests.ConnectTimeout):
        return False


def play_video(plugin_handle, title, icon, stream, media_type='Video'):
    """Start playing given video stream"""
    link = stream.get_link()
    input_stream = 'inputstream.rtmp' if stream.is_rtmp() else 'inputstream.adaptive'
    list_item = xbmcgui.ListItem(label=title, path=link)
    list_item.setArt({'icon': icon})
    list_item.setInfo(type=media_type, infoLabels={"Title": title})
    list_item.setProperty('IsPlayable', 'true')
    list_item.setProperty('inputstream', input_stream)
    list_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    xbmcplugin.setResolvedUrl(plugin_handle, True, listitem=list_item)


def show_notification(heading_string, message_string, icon):
    """Show Kodi notification with given strings"""
    xbmcgui.Dialog().notification(heading_string, message_string, icon)


def show_localized_notification(kodi_helper, heading_string_id, message_string_id, icon=xbmcgui.NOTIFICATION_ERROR):
    """Show Kodi notification with given string ids"""
    show_notification(kodi_helper.get_local_string(heading_string_id), kodi_helper.get_local_string(message_string_id),
                      icon)


def show_available_elh_matches(kodi_helper, tipsport, competitions):
    """Generate list of available elh matches in Kodi"""
    xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
    matches = tipsport.get_list_elh_matches(competitions)
    if len(matches) == 0:
        show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
    for match in matches:
        if match.is_stream_enabled():
            url = kodi_helper.build_url({
                'mode': 'play',
                'url': match.url,
                'name': match.name.encode('utf-8'),
                'start_time': match.start_time
            })
        else:
            url = kodi_helper.build_url({
                'mode': 'notification',
                'title': match.name.encode('utf-8'),
                'message': kodi_helper.get_local_string(30008)
            })
        if match.started:
            status = ''
            if match.status is not None:
                status = match.status.encode('utf-8') if xbmc.getLanguage(xbmc.ISO_639_1) == 'cs' else ''
            plot = '\n{text}: {score:<20}{status}'.format(text=kodi_helper.get_local_string(30003),
                                                          score=match.score or '',
                                                          status=status)
        else:
            plot = '{text} {time}'.format(text=kodi_helper.get_local_string(30002), time=match.start_time)
        possible_match_icon = kodi_helper.get_match_icon(match.first_team, match.second_team)
        if possible_match_icon:
            icon = possible_match_icon
        else:
            icon = kodi_helper.get_media(match.icon_name) if match.icon_name else kodi_helper.icon
        list_item = xbmcgui.ListItem(match.name, iconImage=icon)
        list_item.setThumbnailImage(icon)
        list_item.setInfo(type='Video', infoLabels={'Plot': plot})
        list_item.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item)
    xbmcplugin.endOfDirectory(kodi_helper.plugin_handle)


def show_available_competitions(kodi_helper):
    xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
    # CZ Tipsport Extraliga
    icon = kodi_helper.get_media('cz_tipsport_logo.png')
    list_item = xbmcgui.ListItem('CZ Tipsport Extraliga', iconImage=icon)
    list_item.setThumbnailImage(icon)
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30006)})
    url = kodi_helper.build_url({'mode': 'folder', 'foldername': 'CZ_TIPSPORT'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    # CZ Chance Liga
    icon = kodi_helper.get_media('cz_chance_liga_logo.png')
    list_item = xbmcgui.ListItem('CZ Chance Liga', iconImage=icon)
    list_item.setThumbnailImage(icon)
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30009)})
    url = kodi_helper.build_url({'mode': 'folder', 'foldername': 'CZ_CHANCE'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    # SK Tipsport Liga
    icon = kodi_helper.get_media('sk_tipsport_logo.png')
    list_item = xbmcgui.ListItem('SK Tipsport Liga', iconImage=icon)
    list_item.setThumbnailImage(icon)
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30007)})
    url = kodi_helper.build_url({'mode': 'folder', 'foldername': 'SK_TIPSPORT'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    # TODO: delete

    if kodi_helper.show_all_matches:
        list_item = xbmcgui.ListItem('All')
        list_item.setInfo(type='Video', infoLabels={'Plot': ''})
        url = kodi_helper.build_url({'mode': 'folder', 'foldername': '_ALL'})
        xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(kodi_helper.plugin_handle)


def get_new_tipsport(kodi_helper):
    tipsport = Tipsport(kodi_helper.user_data, None)
    tipsport.login()
    return tipsport


def main():
    kodi_helper = KodiHelper(plugin_handle=int(sys.argv[1]), args=sys.argv[2][1:], base_url=sys.argv[0])
    storage = MemStorage('plugin.video.tipsport.elh_' + kodi_helper.version)
    tipsport_storage_id = 'tsg'
    mode = kodi_helper.get_arg('mode')
    try:
        if mode is None:
            if tipsport_storage_id not in storage:
                storage[tipsport_storage_id] = get_new_tipsport(kodi_helper)
            show_available_competitions(kodi_helper)

        elif mode == 'folder':
            if tipsport_storage_id not in storage:
                storage[tipsport_storage_id] = get_new_tipsport(kodi_helper)
            tipsport = storage[tipsport_storage_id]
            show_available_elh_matches(kodi_helper, tipsport, kodi_helper.get_arg('foldername'))
            storage[tipsport_storage_id] = tipsport

        elif mode == 'play':
            if tipsport_storage_id not in storage:
                storage[tipsport_storage_id] = get_new_tipsport(kodi_helper)
            tipsport = storage[tipsport_storage_id]
            stream = tipsport.get_stream(kodi_helper.get_arg('url'))
            title = '{name} ({time})'.format(name=kodi_helper.get_arg('name'), time=kodi_helper.get_arg('start_time'))
            play_video(kodi_helper.plugin_handle, title, kodi_helper.icon, stream)
            storage[tipsport_storage_id] = tipsport

        elif mode == 'notification':
            show_notification(kodi_helper.get_arg('title'), kodi_helper.get_arg('message'), xbmcgui.NOTIFICATION_INFO)

        elif mode == 'check_login':
            tipsport = get_new_tipsport(kodi_helper)
            if not tipsport.is_logged_in():
                raise LoginFailedException()
            storage[tipsport_storage_id] = tipsport
            show_localized_notification(kodi_helper, 30000, 30001, xbmcgui.NOTIFICATION_INFO)

    except (NoInternetConnectionsException, requests.ConnectionError, requests.ConnectTimeout,
            requests.exceptions.ChunkedEncodingError):
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
    except UnableGetStreamListException:
        show_localized_notification(kodi_helper, 32000, 32010)
    except StrangeXBMCException:
        show_localized_notification(kodi_helper, 32000, 32011)
    except StreamHasNotStarted:
        show_localized_notification(kodi_helper, 30004, 30008, xbmcgui.NOTIFICATION_INFO)
    except TipsportMsg as e:
        xbmcgui.Dialog().ok(kodi_helper.get_local_string(32000), e.message)
    except Exception as e:
        if send_crash_report(kodi_helper, e):
            show_localized_notification(kodi_helper, 32000, 32009)
        else:
            log(traceback.format_exc(e))
            show_localized_notification(kodi_helper, 32000, 32008)


if __name__ == "__main__":
    main()
