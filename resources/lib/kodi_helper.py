# -*- coding: utf-8 -*-
import os
import fnmatch
import urllib
import urlparse
import xbmc
import xbmcaddon
import xbmcvfs
from tipsport_stream_generator import Quality, Site
from tipsport_exceptions import TipsportMsg
from utils import log
try:
    from PIL import Image
    CAN_GENERATE_LOGOS = True
except:
    CAN_GENERATE_LOGOS = False

LOGO_BASEPATH = 'LOGOS'
LOGOS = { # CZ Tipsport
         u'Chomutov':u'chomutov',
         u'Kometa Brno':u'kometa_brno',
         u'Karlovy Vary':u'karlovy_vary',
         u'Liberec':u'liberec',
         u'Litvínov':u'litvinov',
         u'Mladá Boleslav':u'mlada_boleslav',
         u'Hradec Králové':u'hradec_kralove',
         u'Olomouc':u'olomouc',
         u'Pardubice':u'pardubice',
         u'Plzeň':u'plzen',
         u'Sparta Praha':u'sparta_praha',
         u'Třinec':u'trinec',
         u'Vítkovice':u'vitkovice',
         u'Zlín':u'zlin',
         # CZ Chance
         u'Benátky nad Jizerou':u'benatky_nad_jizerou',
         u'České Budějovice':u'ceske_budejovice',
         u'Frýdek-Místek':u'frydek_mistek',
         u'Havířov':u'havirov',
         u'Jihlava':u'jihlava',
         u'Kadaň':u'kadan',
         u'Kladno':u'kladno',
         u'Litoměřice':u'litomerice',
         u'Poruba':u'poruba',
         u'Přerov':u'prerov',
         u'Prostějov':u'prostejov',
         u'Slavia Praha':u'slavia_praha',
         u'Třebíč':u'trebic',
         u'Ústí nad Labem':u'usti_nad_labem',
         u'Vsetín':u'vsetin',
         # SK Tipsport
         u'Košice':u'kosice',
         u'Miskolc':u'miskolc',
         u'Žilina':u'zilina',
         u'Nové Zámky':u'nove_zamky',
         u'Banská Bystrica':u'banska_bystrica',
         u'MAC Budapest':u'budapest',
         u'Detva':u'detva',
         u'Trenčín':u'dukla_trencin',
         u'Liptovský Mikuláš':u'liptovsky_mikulas',
         u'Nitra':u'nitra',
         u'Poprad':u'poprad',
         u'Zvolen':u'zvolen'
        }

class KodiHelper:
    """Store all the configuration data from Kodi"""
    def __init__(self, plugin_handle=None, args=None, base_url=None):
        addon = self.get_addon()
        self.plugin_handle = plugin_handle
        self.args = urlparse.parse_qs(args)
        self.base_url = base_url
        self.plugin_name = 'plugin.video.tipsport.elh'
        self.media_path = xbmc.translatePath('special://home/addons/{0}/resources/media'.format(self.plugin_name))
        self.tmp_path = xbmc.translatePath('special://temp/{0}/'.format(self.plugin_name))
        if not xbmcvfs.exists(self.tmp_path):
            xbmcvfs.mkdirs(self.tmp_path)
        self.version = addon.getAddonInfo('version')
        self.username = addon.getSetting('username')
        self.password = addon.getSetting('password')
        self.quality = self.__get_quality(addon)
        self.site = self.__get_site(addon)
        self.send_crash_reports = True if addon.getSetting('send_crash_reports') == 'true' else False
        self.icon = addon.getAddonInfo('icon')
        self.can_generate_logos = CAN_GENERATE_LOGOS and (addon.getSetting('generate_logos') == 'true')

    @staticmethod
    def __get_quality(addon):
        return Quality.parse(addon.getSetting('quality'))

    @staticmethod
    def __get_site(addon):
        return Site.parse(addon.getSetting('site'))

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
        return os.path.join(self.media_path, name)

    def get_logo(self, name, first=True):
        result = []
        dirs = [self.get_media(LOGO_BASEPATH)]
        while (len(dirs) > 0):
            path = dirs.pop(0)
            folders, files = xbmcvfs.listdir(path)
            dirs.extend([os.path.join(path, folder) for folder in folders])
            result.extend([os.path.join(path, f) for f in fnmatch.filter(files, name)])
            if first and len(result) > 0:
                return result[0]
        return result

    def get_tmp_path(self, name):
        try:
            return os.path.join(self.tmp_path, name)
        except UnicodeDecodeError:
            CAN_GENERATE_LOGOS = False
            return None


    def get_match_icon(self, name_1, name_2):
        if not self.can_generate_logos or name_1 not in LOGOS or name_2 not in LOGOS:
            return None
        filename = '_' + LOGOS[name_1] + '_VS_' + LOGOS[name_2] + ".png"
        path = self.get_tmp_path(filename)
        if path is None:
            return None
        logo_exists = xbmcvfs.exists(path)
        if logo_exists or (not logo_exists and self.generate_icon(LOGOS[name_1], LOGOS[name_2], path)):
            return path
        else:
            return None

    def generate_icon(self, name_1, name_2, path):
        try:
            images = list(map(Image.open, [self.get_logo('vs.png'),
                                           self.get_logo(name_1 + '.png'),
                                           self.get_logo(name_2 + '.png')]))
            new_img = Image.new('RGB', (images[0].width, images[0].height))
            new_img.putalpha(0)
            new_img.paste(images[1], (0,0), images[1])
            new_img.paste(images[2], (int(images[0].width/2),0), images[2])
            new_img.paste(images[0], (0,0), images[0])
            new_img.save(path)
            log('Saved ({0})'.format(path))
            return True
        except:
            return False

    def remove_tmp_logos(self):
        log('Removing old match logos')
        _, logos = xbmcvfs.listdir(self.tmp_path)
        for logo in fnmatch.filter(logos, '_*.png'):
            xbmcvfs.delete(os.path.join(self.tmp_path, logo))

