import urllib
import urlparse
import xbmc
import xbmcaddon


class KodiHelper:
    """Store all the configuration data from Kodi"""
    def __init__(self, plugin_handle=None, args=None, base_url=None):
        addon = self.get_addon()
        self.plugin_handle = plugin_handle
        self.args = urlparse.parse_qs(args)
        self.base_url = base_url
        self.plugin_name = 'plugin.video.tipsport.elh'
        self.media_path = xbmc.translatePath('special://home/addons/{0}/resources/media/'.format(self.plugin_name))
        self.version = addon.getAddonInfo('version')
        self.username = addon.getSetting('username')
        self.password = addon.getSetting('password')
        self.send_crash_reports = True if addon.getSetting('send_crash_reports') == 'true' else False
        self.icon = addon.getAddonInfo('icon')

    @staticmethod
    def get_addon():
        return xbmcaddon.Addon()

    def build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    def get_arg(self, key):
        value = self.args.get(key, None)
        return value if value is None else value[0]

    def get_local_string(self, string_id):
        src = xbmc if string_id < 30000 else self.get_addon()
        localized_string = src.getLocalizedString(string_id)
        if isinstance(localized_string, unicode):
            localized_string = localized_string.encode('utf-8')
        return localized_string

    def get_media(self, name):
        return self.media_path + name
