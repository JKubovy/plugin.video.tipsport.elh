import sys
import xbmc
import xbmcgui
import xbmcplugin
import traceback
import requests
from resources.lib.tipsport_stream_generator import Tipsport
import resources.lib.tipsport_exceptions as Exceptions
from resources.lib.kodi_helper import KodiHelper
from resources.lib.mem_storage import MemStorage
from resources.lib.utils import log, get_host_info


def send_crash_report(kodi_helper, exception):
    """Send crash log to google script to process it"""
    if not kodi_helper.send_crash_reports:
        return False
    try:
        session = requests.session()
        addon = kodi_helper.plugin_name
        version = kodi_helper.version
        data = traceback.format_exc()
        params = {
            'Addon': addon,
            'Version': version,
            'Error': f'{type(exception).__name__}: {str(exception)}',
            'HostInfo': get_host_info(),
            'Traceback': data
        }
        url = 'https://kodiaddonlogcollector20211126141510.azurewebsites.net/api/KodiAddonLogCollector?code=CriVfaPeh2olyCo9X9yqh5F548Ns4DTPgH5Dz8NMDTP9GOp768BwQA=='
        response = session.post(url, json=params)
        if response.ok:
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


def show_all_matches(kodi_helper, tipsport, folder_url):
    """Generate list of all matches in folders (sport -> competition -> match)"""
    url_tokens = folder_url.split('/')
    url_mode = len(url_tokens)
    if url_mode == 1:  # need to show sport folders
        xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
        matches = tipsport.get_list_matches(url_tokens[0])
        if len(matches) == 0:
            show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
        sports = list(set([m.sport for m in matches]))
        for sport in sports:
            url = kodi_helper.build_folder_url(sport, {'mode': 'folder'})
            list_item = xbmcgui.ListItem(sport)
            list_item.setInfo(type='Video', infoLabels={'Plot': sport})
            xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)
        xbmcplugin.endOfDirectory(kodi_helper.plugin_handle, updateListing=True, cacheToDisc=False)
    elif url_mode == 2:  # competition folders
        xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
        matches = tipsport.get_list_matches(url_tokens[0])
        matches = [m for m in matches if m.sport == url_tokens[1]]
        if len(matches) == 0:
            show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
        competitions = list(set([m.competition for m in matches]))
        for competition in competitions:
            url = kodi_helper.build_folder_url(competition, {'mode': 'folder'})
            list_item = xbmcgui.ListItem(competition)
            list_item.setInfo(type='Video', infoLabels={'Plot': competition})
            xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)
        xbmcplugin.endOfDirectory(kodi_helper.plugin_handle, updateListing=True, cacheToDisc=False)
    else:  # match folders
        xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
        matches = tipsport.get_list_matches(url_tokens[0])
        matches = [m for m in matches if m.sport == url_tokens[1] and m.competition == url_tokens[2]]
        if len(matches) == 0:
            show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
        for match in matches:
            add_match_item(match, kodi_helper)
        xbmcplugin.endOfDirectory(kodi_helper.plugin_handle, updateListing=True, cacheToDisc=False)


def add_match_item(match, kodi_helper):
    if match.is_stream_enabled():
        url = kodi_helper.build_url({
            'mode': 'play',
            'url': match.url,
            'name': match.name,
            'start_time': match.start_time
        })
    else:
        url = kodi_helper.build_url({
            'mode': 'notification',
            'title': match.name,
            'message': kodi_helper.get_local_string(30008)
        })
    if match.started:
        plot = '\n{text}: {score:<20}{status}'.format(
            text=kodi_helper.get_local_string(30003),
            score=match.score or '',  # If score is None TypeError is thrown
            status=match.status if xbmc.getLanguage(xbmc.ISO_639_1) == 'cs' else '')
    else:
        plot = '{text} {time}'.format(text=kodi_helper.get_local_string(30002), time=match.start_time)
    possible_match_icon = kodi_helper.get_match_icon(match.first_team, match.second_team,
                                                     match.is_competition_with_logo)
    if possible_match_icon:
        icon = possible_match_icon
    else:
        icon = kodi_helper.get_media(match.icon_name) if match.icon_name else kodi_helper.icon
    list_item = xbmcgui.ListItem(match.name)
    list_item.setArt({'icon': icon})
    list_item.setInfo(type='Video', infoLabels={'Plot': plot})
    list_item.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item)


def show_available_elh_matches(kodi_helper, tipsport, competitions):
    """Generate list of available elh matches in Kodi"""
    xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
    matches = tipsport.get_list_matches(competitions)
    if len(matches) == 0:
        show_localized_notification(kodi_helper, 30004, 30005, xbmcgui.NOTIFICATION_INFO)
    for match in matches:
        add_match_item(match, kodi_helper)
    xbmcplugin.endOfDirectory(kodi_helper.plugin_handle, updateListing=True, cacheToDisc=False)


def show_available_competitions(kodi_helper):
    xbmcplugin.setContent(kodi_helper.plugin_handle, 'movies')
    # CZ Tipsport Extraliga
    icon = kodi_helper.get_media('cz_tipsport_logo.png')
    list_item = xbmcgui.ListItem('CZ Tipsport Extraliga')
    list_item.setArt({'icon': icon})
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30006)})
    url = kodi_helper.build_folder_url('CZ_TIPSPORT', {'mode': 'folder'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    # CZ Chance Liga
    icon = kodi_helper.get_media('cz_chance_liga_logo.png')
    list_item = xbmcgui.ListItem('CZ Chance Liga')
    list_item.setArt({'icon': icon})
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30009)})
    url = kodi_helper.build_folder_url('CZ_CHANCE', {'mode': 'folder'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    # SK Tipsport Liga
    icon = kodi_helper.get_media('sk_tipsport_logo.png')
    list_item = xbmcgui.ListItem('SK Tipsport Liga')
    list_item.setArt({'icon': icon})
    list_item.setInfo(type='Video', infoLabels={'Plot': kodi_helper.get_local_string(30007)})
    url = kodi_helper.build_folder_url('SK_TIPSPORT', {'mode': 'folder'})
    xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    if kodi_helper.show_all_matches:
        list_item = xbmcgui.ListItem('All')
        list_item.setInfo(type='Video', infoLabels={'Plot': ''})
        url = kodi_helper.build_folder_url('_ALL', {'mode': 'folder'})
        xbmcplugin.addDirectoryItem(handle=kodi_helper.plugin_handle, url=url, listitem=list_item, isFolder=True)

    xbmcplugin.endOfDirectory(kodi_helper.plugin_handle)


def get_new_tipsport(kodi_helper):
    tipsport = Tipsport(kodi_helper, None)
    if not tipsport.is_logged_in():
        tipsport.login()
    return tipsport


def show_support_dialog(kodi_helper):
    xbmcgui.Dialog().textviewer(kodi_helper.get_local_string(32013), kodi_helper.get_local_string(32014))


def get_tipsport_from_storage_add_save_it(storage, id, kodi_helper):
    if id not in storage:
        tipsport = get_new_tipsport(kodi_helper)
        storage[id] = tipsport
        return tipsport
    try:
        return storage[id]
    except UnicodeEncodeError:
        tipsport = get_new_tipsport(kodi_helper)
        storage[id] = tipsport
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
            if kodi_helper.is_time_to_show_support_dialog():
                show_support_dialog(kodi_helper)

        elif mode == 'folder':
            tipsport = get_tipsport_from_storage_add_save_it(storage, tipsport_storage_id, kodi_helper)
            folder_url = kodi_helper.get_folder()
            log(f'Folder url: "{folder_url}"')
            if folder_url.startswith('_ALL') and kodi_helper.put_all_matches_in_folders:
                show_all_matches(kodi_helper, tipsport, folder_url)
            else:
                show_available_elh_matches(kodi_helper, tipsport, folder_url)
            storage[tipsport_storage_id] = tipsport

        elif mode == 'play':
            tipsport = get_tipsport_from_storage_add_save_it(storage, tipsport_storage_id, kodi_helper)
            stream = tipsport.get_stream(kodi_helper.get_arg('url'))
            title = '{name} ({time})'.format(name=kodi_helper.get_arg('name'), time=kodi_helper.get_arg('start_time'))
            play_video(kodi_helper.plugin_handle, title, kodi_helper.icon, stream)
            storage[tipsport_storage_id] = tipsport

        elif mode == 'notification':
            show_notification(kodi_helper.get_arg('title'), kodi_helper.get_arg('message'), xbmcgui.NOTIFICATION_INFO)

        elif mode == 'check_login':
            tipsport = get_new_tipsport(kodi_helper)
            if not tipsport.is_logged_in():
                raise Exceptions.LoginFailedException()
            storage[tipsport_storage_id] = tipsport
            show_localized_notification(kodi_helper, 30000, 30001, xbmcgui.NOTIFICATION_INFO)

    except (Exceptions.NoInternetConnectionsException, requests.ConnectionError, requests.ConnectTimeout,
            requests.exceptions.ChunkedEncodingError):
        log(traceback.format_exc())
        show_localized_notification(kodi_helper, 32000, 32001)
    except Exceptions.LoginFailedException:
        show_localized_notification(kodi_helper, 32000, 32002)
    except Exceptions.UnableGetStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32003)
    except Exceptions.UnableParseStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32004)
    except Exceptions.UnsupportedFormatStreamMetadataException:
        show_localized_notification(kodi_helper, 32000, 32005)
    except Exceptions.UnableDetectScriptSessionIdException:
        show_localized_notification(kodi_helper, 32000, 32006)
    except Exceptions.UnableGetStreamNumberException:
        show_localized_notification(kodi_helper, 32000, 32007)
    except Exceptions.UnableGetStreamListException:
        show_localized_notification(kodi_helper, 32000, 32010)
    except Exceptions.StrangeXBMCException:
        show_localized_notification(kodi_helper, 32000, 32011)
    except Exceptions.NeedPluginUpdateException:
        show_localized_notification(kodi_helper, 32000, 32012)
    except Exceptions.StreamHasNotStarted:
        show_localized_notification(kodi_helper, 30004, 30008, xbmcgui.NOTIFICATION_INFO)
    except Exceptions.TipsportMsg as e:
        xbmcgui.Dialog().ok(kodi_helper.get_local_string(32000), str(e))
    except Exception as e:
        if send_crash_report(kodi_helper, e):
            show_localized_notification(kodi_helper, 32000, 32009)
        else:
            log(traceback.format_exc())
            show_localized_notification(kodi_helper, 32000, 32008)


if __name__ == "__main__":
    main()
