# coding=utf-8
import os
import fnmatch
import urllib
import urlparse
import xbmc
import xbmcaddon
from tipsport_stream_generator import Quality
from tipsport_exceptions import TipsportMsg
try:
    import os
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
         u'Slavia':u'slavia_praha',
         u'Třebíč':u'trebic',
         u'Ústí nad Labem':u'usti_nad_labem',
         u'Vsetín':u'vsetin'
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
        self.tmp_path = xbmc.translatePath('special://temp/{0}'.format(self.plugin_name))
        if not os.path.exists(self.tmp_path):
            os.makedirs(self.tmp_path)
        self.version = addon.getAddonInfo('version')
        self.username = addon.getSetting('username')
        self.password = addon.getSetting('password')
        self.quality = self.__get_quality(addon)
        self.send_crash_reports = True if addon.getSetting('send_crash_reports') == 'true' else False
        self.icon = addon.getAddonInfo('icon')
        self.can_generate_logos = CAN_GENERATE_LOGOS and (addon.getSetting('generate_logos') == 'true')

    @staticmethod
    def __get_quality(addon):
        return Quality.parse(addon.getSetting('quality'))

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
        for root, _ , filenames in os.walk(self.get_media(LOGO_BASEPATH)):
            for filename in fnmatch.filter(filenames, name):
                if first:
                    return os.path.join(root, filename)
                else:
                    result.append(os.path.join(root, filename))
        return result

    def get_tmp_path(self, name):
        return os.path.join(self.tmp_path, name)

    def get_match_icon(self, name_1, name_2):
        if not self.can_generate_logos or name_1 not in LOGOS or name_2 not in LOGOS:
            return None
        filename = '_' + LOGOS[name_1] + '_VS_' + LOGOS[name_2] + ".png"
        #path = self.get_tmp_path(filename)
        path = self.get_media(os.path.join(LOGO_BASEPATH, filename))
        logo_exists = os.path.isfile(path)
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
            return True
        except:
            return False

    def remove_tmp_logos(self):
        logos = self.get_logo('_*')
        for logo in logos:
            os.remove(logo)
