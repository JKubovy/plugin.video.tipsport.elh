# coding=utf-8
import re
import random
import json
import requests
import urllib
import time
from datetime import datetime, timedelta
import _strptime
import xml.etree.ElementTree
from tipsport_exceptions import *

COMPETITIONS = {'CZ_TIPSPORT': [u'Česká Tipsport extraliga', u'Tipsport extraliga', u'CZ Tipsport extraliga'],
                'SK_TIPSPORT': [u'Slovenská Tipsport liga', u'Slovensk\u00E1 Tipsport liga', u'Tipsport Liga'],
                'CZ_CHANCE': [u'Česká Chance liga', u'CZ Chance liga']
               }
FULL_NAMES = {u'H.Králové': u'Hradec Králové',
              u'M.Boleslav': u'Mladá Boleslav',
              u'K.Vary': u'Karlovy Vary',
              u'SR 20': u'Slovensko 20',
              u'L.Mikuláš': u'Liptovský Mikuláš',
              u'N.Zámky': u'Nové Zámky',
              u'HK Poprad': u'Poprad',
              u'B.Bystrica': u'Banská Bystrica',
              u'Fr.Místek':u'Frýdek-Místek',
              u'Ústí': u'Ústí nad Labem',
              u'Benátky': u'Benátky nad Jizerou',
              u'Č.Budějovice': u'České Budějovice'
              }
COMPETITION_LOGO = {'CZ_TIPSPORT': 'cz_tipsport_logo.png',
                    'SK_TIPSPORT': 'sk_tipsport_logo.png',
                    'CZ_CHANCE': 'cz_chance_liga_logo.png'
                   }


class Quality(object):
    @staticmethod
    def parse(str_quality):
        if str_quality == '0':
            return Quality.LOW
        elif str_quality == '1':
            return Quality.MID
        elif str_quality == '2':
            return Quality.HIGH
        else:
            raise UnknownException('Unknown quality')
    LOW = 0
    MID = 1
    HIGH = 2


class Match:
    """Class represents one match with additional information"""

    def __init__(self, name, competition, sport, url, start_time, status, not_started, score, icon_name,
                 minutes_enable_before_start):
        self.first_team, self.second_team, self.name = self.parse_name(name)
        self.competition = competition
        self.sport = sport
        self.url = url
        self.start_time = start_time
        self.status = status
        self.started = True if not_started in ['false', False] else False
        self.score = score
        self.icon_name = icon_name
        self.minutes_enable_before_start = minutes_enable_before_start
        self.match_time = self.get_match_time()
    
    def get_match_time(self):
        now = datetime.now()
        match_time = datetime(*(time.strptime(self.start_time, '%H:%M')[0:6]))
        match_time = datetime.now().replace(hour=match_time.hour, minute=match_time.minute, second=0, microsecond=0)
        return match_time

    def is_stream_enabled(self):
        time_to_start = self.match_time - datetime.now()
        if time_to_start.days < 0:
            return True
        else:
            return time_to_start.seconds < timedelta(minutes=self.minutes_enable_before_start).seconds

    @staticmethod
    def get_full_name_if_possible(name):
        if name in FULL_NAMES:
            return FULL_NAMES[name]
        else:
            return name

    @staticmethod
    def parse_name(name):
        try:
            (first_team, second_team) = name.split('-')
            first_team = Match.get_full_name_if_possible(first_team)
            second_team = Match.get_full_name_if_possible(second_team)
            match_name = u'{first_team} - {second_team}'.format(first_team=first_team, second_team=second_team)
            return (first_team, second_team, match_name)
        except ValueError:
            return name


class RTMPStream:
    """Class represent one stream and store metadata used to generate rtmp stream link"""

    def __init__(self, rtmp_url, playpath, app, live_stream):
        self.rtmp_url = rtmp_url
        self.playpath = playpath
        self.app = app
        self.live_stream = live_stream

    def get_link(self):
        return '{rtmp_url} playpath={playpath} app={app}{live}'.format(rtmp_url=self.rtmp_url,
                                                                       playpath=self.playpath,
                                                                       app=self.app,
                                                                       live=' live=true' if self.live_stream else '')


class HLSStream:
    """Class represent one stream and store metadata used to generate hls stream link"""

    def __init__(self, url):
        self.url = url.strip()

    def get_link(self):
        return self.url


class Tipsport:
    """Class providing communication with Tipsport.cz site"""

    def __init__(self, username, password, quality):
        self.session = requests.session()
        self.logged_in = False
        self.username = username
        self.password = password
        self.quality = quality

    def login(self):
        """Login to https://m.tipsport.cz site with given credentials"""
        page = self.session.get('https://m.tipsport.cz')  # load cookies
        id = re.search('__SESSID = \'(.*?)\';', page.text)
        if (id):
            token = id.group(1)
            self.session.headers.update({'X-Auth-Token': token})
        else:
            raise LoginFailedException()
        payload = {'username': self.username,
			        'password': self.password,
			        'redirect': '/',
			        'token': token}
        try:
            self.session.post('https://m.tipsport.cz/rest/client/v1/session', payload)  # actual login
        except Exception as e:
            raise e.__class__   # remove tipsport account credentials from traceback
        self.check_login()

    def check_login(self):
        """Check if login to https://m.tipsport.cz was successful"""
        page = self.session.get('https://m.tipsport.cz')
        success = re.search('\'logged\': \'(.*?)\'', page.text)
        if (success):
            self.logged_in = success.group(1) == 'true'
        if (not self.logged_in):
            raise LoginFailedException()

    def get_matches_both_menu_response(self):
        """Get dwr respond with all matches today"""
        response = self.session.get('https://m.tipsport.cz/rest/articles/v1/tv/program?day=0&articleId=')
        response.encoding = 'utf-8'
        if ('days' not in response.text):
            raise UnableGetStreamListException()
        else:
            return response

    def get_list_elh_matches(self, competition_name):
        """Get list of all available ELH matches on https://www.tipsport.cz/tv"""
        response = self.get_matches_both_menu_response()
        data = json.loads(response.text)
        if competition_name in COMPETITION_LOGO:
            icon_name = COMPETITION_LOGO[competition_name]
        else:
            icon_name = None
        matches = []
        for sport in data['program']:
            if sport['id'] == 23:
                for part in sport['matchesByTimespans']:
                    for match in part:
                        if match['competition'] in COMPETITIONS[competition_name]:
                            matches.append(Match(name=match['name'],
											     competition=match['competition'],
											     sport=match['sport'],
											     url=match['url'],
											     start_time=match['matchStartTime'],
											     status=match['score']['statusOffer'],
											     not_started=not match['live'],
											     score=match['score']['scoreOffer'],
											     icon_name=icon_name,
                                                 minutes_enable_before_start=15))
        matches.sort(key=lambda match: match.match_time)
        return matches

    def get_response_dwr_get_stream(self, relative_url, c0_param1):
        stream_url = 'https://www.tipsport.cz/live' + relative_url
        page = self.session.get(stream_url)
        token = get_token(page.text)
        relative_url = relative_url.split('#')[0]
        dwr_script = 'https://www.tipsport.cz/dwr/call/plaincall/StreamDWR.getStream.dwr'
        payload = {'callCount': 1,
                    'page': relative_url,
                    'httpSessionId': '',
                    'scriptSessionId': token,
                    'c0-scriptName': 'StreamDWR',
                    'c0-methodName': 'getStream',
                    'c0-id': 0,
                    'c0-param0': 'number:{0}'.format(get_stream_number(relative_url)),
                    'c0-param1': 'string:{0}'.format(c0_param1),
                    'batchId': 9}
        response = self.session.post(dwr_script, payload)
        return response

    def get_hls_stream_from_dwr(self, relative_url):
        response = self.get_response_dwr_get_stream(relative_url, 'HLS')
        url = re.search('value:"(.*?)"', response.text)
        if not url:
            raise UnableGetStreamMetadataException()
        return self.get_hls_stream(url.group(1))

    def get_hls_stream_from_page(self, page):
        next_hop = re.search('<iframe src="(.*?embed.*?)"', page)
        if not next_hop:
            raise UnableGetStreamMetadataException()
        page = self.session.get(next_hop.group(1))
        next_hop = re.search('"hls": "(.*?)"', page.text)
        if not next_hop:
            raise UnableGetStreamMetadataException()
        return self.get_hls_stream(next_hop.group(1))

    def __select_stream_by_quality(self, list_of_streams):
        """List is ordered from the lowest to the best quality"""
        if len(list_of_streams) <= 0:
            raise UnableGetStreamMetadataException('List of streams by quality is empty')
        if len(list_of_streams) > self.quality:
            return list_of_streams[self.quality]
        else:
            if self.quality in [Quality.LOW, Quality.MID]:
                return list_of_streams[0]
            else:
                return list_of_streams[-1]

    def get_hls_stream(self, url, reverse_order=False):
        url = url.replace('\\', '')
        response = self.session.get(url)
        if 'm3u8' not in response.text:
            raise StreamHasNotStarted()
        playlists = [playlist for playlist in response.text.split('\n') if not playlist.startswith('#')]
        playlists = [playlist for playlist in playlists if playlist != '']
        if reverse_order:
            playlists.reverse()
        playlist_relative_link = self.__select_stream_by_quality(playlists)
        playlist = url.replace('playlist.m3u8', playlist_relative_link)
        return HLSStream(playlist)

    def get_rtmp_stream(self, relative_url):
        response = self.get_response_dwr_get_stream(relative_url, 'SMIL')
        search_type = re.search('type:"(.*?)"', response.text)
        response_type = search_type.group(1) if search_type else 'ERROR'
        if response_type == 'ERROR':  # use 'string:RTMP' instead of 'string:SMIL'
            response = self.get_response_dwr_get_stream(relative_url, 'RTMP')
        search_type = re.search('type:"(.*?)"', response.text)
        response_type = search_type.group(1) if search_type else 'ERROR'
        if response_type == 'ERROR':  # StreamDWR.getStream.dwr not working on this specific stream
            raise UnableGetStreamMetadataException()
        if response_type == 'RTMP_URL':
            if re.search('value:"?(.*?)"?}', response.content.decode('unicode-escape')).group(1).lower() == 'null':
                raise UnableGetStreamMetadataException()
            urls = re.findall('(rtmp.*?)"',
                                response.content.decode('unicode-escape'))
            urls.reverse()
            urls = [url.replace(r'\u003d', '=') for url in urls]
            urls = [url.replace('\\', '') for url in urls]
            url = self.__select_stream_by_quality(urls)
            return parse_stream_dwr_response('"RTMP_URL":"{url}"'.format(url=url))
        else:
            response_url = re.search('value:"(.*?)"', response.text)
            url = response_url.group(1)
            url = url.replace('\\', '')
            response = self.session.get(url)
            stream = parse_stream_dwr_response(response.text)
            return stream

    def decode_rtmp_url(self, url):
        try:
            playpath = (url.split('/'))[-1]
            url = url.replace('/' + playpath, '')
            tokens = url.split('/')
            app = '/'.join([tokens[-2], tokens[-1]])
            return RTMPStream(url, playpath, app, True)
        except IndexError:
            raise UnableParseStreamMetadataException()

    def get_stream(self, relative_url):
        """Get instance of Stream class from given relative link"""
        if not self.logged_in:
            self.login()
        alert_text = self.get_alert_message()
        if alert_text:
            raise TipsportMsg(alert_text)
        stream_source, stream_type, url = self.get_stream_source_type_and_data(relative_url)
        if stream_source == 'LIVEBOX_ELH':
            if stream_type == 'RTMP':
                return self.decode_rtmp_url(url)
            elif stream_type == 'HLS':
                return self.get_hls_stream(url, True)
            else:
                raise UnableGetStreamMetadataException()
        elif stream_source == 'MANUAL':
            stream_url = 'https://www.tipsport.cz/live' + relative_url
            page = self.session.get(stream_url)
            return self.get_hls_stream_from_page(page.text)
        elif stream_source == 'HUSTE':
            return self.get_hls_stream(url)
        else:
            raise UnableGetStreamMetadataException()

    def get_alert_message(self):
        """
        Return any alert message from Tipsport (like bet request)
        Return None if everything is OK
        """
        page = self.session.get('https://m.tipsport.cz/rest/articles/v1/tv/info')
        name = 'buttonDescription'
        try:
            data = json.loads(page.text)
            if not name in data:
                raise TipsportMsg()
            text = data[name]
            if text is None:
                return None
            else:
                return text.split('.')[0] + '.'
        except TypeError:
            raise UnableGetStreamMetadataException()
    
    @staticmethod
    def _parse_stream_info_response(response):
        data = json.loads(response.text)
        if data['displayRules'] == None:
            raise(TipsportMsg(data['data']))
        #if data['returnCode']['name'] == 'NOT_STARTED':
        #    raise StreamHasNotStarted()
        stream_source = data['source']
        stream_type = data['type']
        if stream_source is None or stream_type is None:
            raise UnableGetStreamMetadataException()
        return stream_source, stream_type, data['data']

    def get_stream_source_type_and_data(self, relative_url):
        """Get source and type of stream"""
        stream_number = get_stream_number(relative_url)
        foramt = 'HLS'
        base_url = 'https://m.tipsport.cz/rest/offer/v2/live/matches/{stream_number}/stream?deviceType=DESKTOP'.format(stream_number=stream_number)
        url = base_url + '&format=HLS'
        response = self.session.get(url)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if not 'auth=' in data:
                url = base_url + '&format=RTMP'
                response = self.session.get(url)
                stream_source, stream_type, data = self._parse_stream_info_response(response)
            return stream_source, stream_type, data
        except (TypeError, KeyError):
            raise UnableGetStreamMetadataException()


def generate_random_number():
    """Generate string with given length that contains random numbers"""
    result = ''.join(random.SystemRandom().choice('0123456789') for _ in range(10))
    result = result + '-' + ''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
    return result


def parse_stream_dwr_response(response_text):
    """Parse response and try to get stream metadata"""
    response_text = str(urllib.unquote(response_text))
    if '<smil>' in response_text:
        try:
            url = (re.search('meta base="(.*?)"', response_text)).group(1)
            playpath = (re.search('video src="(.*?)"', response_text)).group(1)
            app = (url.split(':80/'))[1]
        except (AttributeError, IndexError):
            raise UnableParseStreamMetadataException()
    elif '<data>' in response_text:
        try:
            response_text = response_text.replace('&amp;', '&')
            url = (re.search('url="(.*?)"', response_text)).group(1)
            auth = (re.search('auth="(.*)"', response_text)).group(1)
            stream = (re.search('stream="(.*)"', response_text)).group(1)
            app = url.split('/')[1]
            url = 'rtmp://' + url
            playpath = '{app}/{stream}?auth={auth}'.format(app=app, stream=stream, auth=auth)
            if 'aifp="v001"' in response_text:
                playpath = playpath + '&aifp=1'
        except (AttributeError, IndexError):
            raise UnableParseStreamMetadataException()
    elif 'videohi' in response_text:
        try:
            url = (re.search('videohi=(.*?)&', response_text)).group(1)
            app = (url.split('/'))[3]
            playpath = app + '/' + (url.split(app + '/'))[1]
            url = (url.split(app + '/'))[0] + app
        except (AttributeError, IndexError):
            raise UnableParseStreamMetadataException()
    elif 'rtmpUrl' in response_text:
        try:
            url = (re.search('"rtmpUrl":"(.*?)"', response_text)).group(1)
            app = (url.split('/'))[3]
            playpath = app + '/' + (url.split(app + '/'))[1]
            url = (url.split(app + '/'))[0] + app
        except (AttributeError, IndexError):
            raise UnableParseStreamMetadataException()
    elif 'RTMP_URL' in response_text:
        try:
            url = (re.search('"RTMP_URL":"(.*?)"', response_text)).group(1)
            playpath = (url.split('/'))[-1]
            url = url.replace('/' + playpath, '')
            tokens = url.split('/')
            app = '/'.join([tokens[-2], tokens[-1]])
        except (AttributeError, IndexError):
            raise UnableParseStreamMetadataException()
    else:
        raise UnsupportedFormatStreamMetadataException()
    return RTMPStream(url, playpath, app, True)


def get_token(page):
    """Get scriptSessionId from page for proper DWRScript call"""
    token = re.search('JAWR.dwr_scriptSessionId=\'([0-9A-Z]+)\'', page)
    if token is None:
        raise UnableDetectScriptSessionIdException()
    token = token.group(1)
    return token


def get_stream_number(relative_url):
    """
    Get stream number from relative URL
    Example:
        /tenis-marterer-maximilian-petrovic-danilo/2768186 -> 2768186
    """
    base_url = relative_url.split('#')[0]
    tokens = base_url.split('/')
    number = tokens[-1]
    try:
        int(number)
    except ValueError:
        raise UnableGetStreamNumberException()
    return number
