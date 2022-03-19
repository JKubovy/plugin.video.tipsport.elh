# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import time
import os
import fnmatch
from urllib.parse import parse_qs, urlencode
import xbmc
import xbmcaddon
import xbmcvfs
from .tipsport_exceptions import StrangeXBMCException
from .site import Site
from .user_data import UserData
from .utils import log
try:
    from PIL import Image
    CAN_GENERATE_LOGOS = True
except Exception:
    CAN_GENERATE_LOGOS = False

LAST_SHOW_DIALOG_FILENAME = 'DIALOG_SHOWN.time'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DIALOG_INTERVAL = timedelta(days=60)
LOGO_BASEPATH = 'LOGOS'
LOGOS = {  # CZ Tipsport
    u'České Budějovice': u'ceske_budejovice',
    u'Kometa Brno': u'kometa_brno',
    u'Karlovy Vary': u'karlovy_vary',
    u'Liberec': u'liberec',
    u'Litvínov': u'litvinov',
    u'Mladá Boleslav': u'mlada_boleslav',
    u'Hradec Králové': u'hradec_kralove',
    u'Olomouc': u'olomouc',
    u'Pardubice': u'pardubice',
    u'Plzeň': u'plzen',
    u'Sparta Praha': u'sparta_praha',
    u'Třinec': u'trinec',
    u'Vítkovice': u'vitkovice',
    u'Zlín': u'zlin',
    # CZ Chance
    u'Benátky nad Jizerou': u'benatky_nad_jizerou',
    u'Frýdek-Místek': u'frydek_mistek',
    u'Havířov': u'havirov',
    u'Jihlava': u'jihlava',
    u'Kadaň': u'kadan',
    u'Kladno': u'kladno',
    u'Kolín': u'kolin',
    u'Litoměřice': u'litomerice',
    u'Poruba': u'poruba',
    u'Přerov': u'prerov',
    u'Prostějov': u'prostejov',
    u'Slavia Praha': u'slavia_praha',
    u'Sokolov': u'sokolov',
    u'Šumperk': u'sumperk',
    u'Třebíč': u'trebic',
    u'Ústí nad Labem': u'usti_nad_labem',
    u'Vrchlabí': u'vrchlabi',
    u'Vsetín': u'vsetin',
    # SK Tipsport
    u'Košice': u'kosice',
    u'Miskolc': u'miskolc',
    u'Žilina': u'zilina',
    u'Nové Zámky': u'nove_zamky',
    u'Banská Bystrica': u'banska_bystrica',
    u'MAC Budapest': u'budapest',
    u'Detva': u'detva',
    u'Trenčín': u'dukla_trencin',
    u'Liptovský Mikuláš': u'liptovsky_mikulas',
    u'Nitra': u'nitra',
    u'Poprad': u'poprad',
    u'Zvolen': u'zvolen',
    u'Michalovce': u'michalovce',
    u'Slovan': u'slovan',
    # OLD
    u'Chomutov': u'chomutov'
}


class KodiHelper:
    """Store all the configuration data from Kodi"""
    def __init__(self, plugin_handle=None, args=None, base_url=None):
        addon = self.get_addon()
        self.plugin_handle = plugin_handle
        self.args = parse_qs(args)
        self.base_url = base_url
        self.plugin_name = addon.getAddonInfo('id')
        self.media_path = xbmcvfs.translatePath('special://home/addons/{0}/resources/media'.format(self.plugin_name))
        self.lib_path = xbmcvfs.translatePath('special://home/addons/{0}/resources/lib'.format(self.plugin_name))
        self.addon_data_path = xbmcvfs.translatePath('special://home/userdata/addon_data/{0}/'.format(self.plugin_name))
        self.tmp_path = xbmcvfs.translatePath('special://temp/{0}/'.format(self.plugin_name))
        if not xbmcvfs.exists(self.tmp_path):
            xbmcvfs.mkdirs(self.tmp_path)
        self.version = addon.getAddonInfo('version')
        self.user_data = UserData(addon.getSetting('username'), addon.getSetting('password'), self.__get_site(addon))
        self.send_crash_reports = addon.getSetting('send_crash_reports') == 'true'
        self.show_all_matches = addon.getSetting('show_all_matches') == 'true'
        self.put_all_matches_in_folders = addon.getSetting('folder_structure_all_matches') == 'true'
        self.icon = addon.getAddonInfo('icon')
        self.can_generate_logos_settings = addon.getSetting('generate_logos') == 'true'

    @property
    def can_generate_logos(self):
        return CAN_GENERATE_LOGOS and self.can_generate_logos_settings

    @staticmethod
    def __get_site(addon):
        return Site.parse(addon.getSetting('site'))

    @staticmethod
    def get_addon():
        try:
            return xbmcaddon.Addon()
        except Exception:
            raise StrangeXBMCException()

    def is_time_to_show_support_dialog(self):
        file_path = os.path.join(self.addon_data_path, LAST_SHOW_DIALOG_FILENAME)
        if not os.path.exists(file_path):
            old_time = datetime.today() - timedelta(days=365)
            with open(file_path, 'w') as f:
                f.write(old_time.strftime(DATE_FORMAT))
        with open(file_path, 'r') as f:
            content = f.read()
            try:
                last_time = datetime.fromtimestamp(time.mktime(time.strptime(content, DATE_FORMAT)))
            except ValueError:
                last_time = old_time

        if last_time > datetime.today() or last_time < (datetime.today() - DIALOG_INTERVAL):
            with open(file_path, 'w') as f:
                f.write(datetime.today().strftime(DATE_FORMAT))
            return True
        else:
            return False

    def build_url(self, query):
        return self.base_url + '?' + urlencode(query)

    def build_folder_url(self, folder, query):
        return self.base_url + folder + '/?' + urlencode(query)

    def get_folder(self):
        return self.base_url.lstrip(f'plugin://{self.plugin_name}/').rstrip('/')

    def get_arg(self, key):
        value = self.args.get(key, None)
        return value if value is None else value[0]

    def get_local_string(self, string_id):
        src = xbmc if string_id < 30000 else self.get_addon()
        localized_string = src.getLocalizedString(string_id)
        return localized_string

    def get_media(self, name):
        return os.path.join(self.media_path, name)

    def get_logo(self, name, first=True):
        result = []
        dirs = [self.get_media(LOGO_BASEPATH)]
        while len(dirs) > 0:
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
            global CAN_GENERATE_LOGOS
            CAN_GENERATE_LOGOS = False
            return None

    def get_match_icon(self, name_1, name_2, is_competition_with_logo):
        if not is_competition_with_logo:
            return None
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
            images = list(
                map(Image.open,
                    [self.get_logo('vs.png'),
                     self.get_logo(name_1 + '.png'),
                     self.get_logo(name_2 + '.png')]))
            new_img = Image.new('RGB', (images[0].width, images[0].height))
            new_img.putalpha(0)
            new_img.paste(images[1], (0, 0), images[1])
            new_img.paste(images[2], (int(images[0].width / 2), 0), images[2])
            new_img.paste(images[0], (0, 0), images[0])
            new_img.save(path)
            log('Saved ({0})'.format(path))
            return True
        except Exception:
            return False

    def remove_tmp_logos(self):
        log('Removing old match logos')
        _, logos = xbmcvfs.listdir(self.tmp_path)
        for logo in fnmatch.filter(logos, '_*.png'):
            xbmcvfs.delete(os.path.join(self.tmp_path, logo))
