# coding=utf-8
import re
import random
import requests
import urllib
import time
from datetime import datetime, timedelta
import _strptime
from tipsport_exceptions import *

COMPETITIONS = {'CZ_TIPSPORT': [u'Tipsport extraliga', u'CZ Tipsport extraliga'],
                'SK_TIPSPORT': [u'Slovensk\u00E1 Tipsport liga', u'Tipsport Liga']}
FULL_NAMES = {u'H.Králové': u'Hradec Králové',
              u'M.Boleslav': u'Mladá Boleslav',
              u'SR 20': u'Slovensko 20',
              u'L.Mikuláš': u'Liptovský Mikuláš',
              u'N.Zámky': u'Nové Zámky',
              u'HK Poprad': u'Poprad',
              u'B.Bystrica': u'Banská Bystrica'}


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
        self.name = self.parse_name(name)
        self.competition = competition
        self.sport = sport
        self.url = url
        self.start_time = start_time
        self.status = status
        self.started = True if not_started == 'false' else False
        self.score = score
        self.icon_name = icon_name
        self.minutes_enable_before_start = minutes_enable_before_start

    def is_stream_enabled(self):
        now = datetime.now()
        match_time = datetime(*(time.strptime(self.start_time, '%H:%M')[0:6]))
        match_time = datetime.now().replace(hour=match_time.hour, minute=match_time.minute, second=0, microsecond=0)
        time_to_start = match_time - now
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
            return u'{first_team} - {second_team}'.format(first_team=first_team, second_team=second_team)
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
        """Login to https://www.tipsport.cz site with given credentials"""
        agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 " \
                "Safari/537.36 OPR/42.0.2393.137 "
        try:
            self.session.get('https://www.tipsport.cz/')  # load cookies
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()
        payload = {'agent': agent,
                   'requestURI': '/',
                   'fPrint': generate_random_number(10),
                   'userName': self.username,
                   'password': self.password}
        try:
            try:
                self.session.post('https://www.tipsport.cz/LoginAction.do', payload)  # actual login
            except Exception as e:
                raise e.__class__   # remove tipsport account credentials from traceback
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()
        self.check_login()

    def check_login(self):
        """Check if login to https://www.tipsport.cz was successful"""
        try:
            page = self.session.get('https://www.tipsport.cz/')
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()
        if 'LogoutAction.do' not in page.text:
            raise LoginFailedException()
        self.logged_in = True

    def get_matches_both_menu_response(self):
        """Get dwr respond with all matches today"""
        try:
            page = self.session.get('https://www.tipsport.cz/tv')
            token = get_token(page.text)
            dwr_script = 'https://www.tipsport.cz/dwr/call/plaincall/LiveOdds2DWR.getMatchesBothMenu.dwr'
            payload = {'callCount': 1,
                       'page': '/tv',
                       'httpSessionId': '',
                       'scriptSessionId': token,
                       'c0-scriptName': 'LiveOdds2DWR',
                       'c0-methodName': 'getMatchesBothMenu',
                       'c0-id': 0,
                       'c0-param0': 'number:0',
                       'c0-param1': 'number:0',
                       'c0-param2': 'boolean:true',
                       'batchId': 2}
            response = self.session.post(dwr_script, payload)
            response.encoding = 'utf-8'
            return response
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()

    def get_list_elh_matches(self, competition_name):
        """Get list of all available ELH matches on https://www.tipsport.cz/tv"""
        response = self.get_matches_both_menu_response()
        matches_iter = re.finditer('.*\
abbrName="(?P<name>.*?) ?".*\
competition="(?P<competition>.*?)".*\
dateStartAsHHMM="(?P<start_time>.*?)".*\
notStarted=(?P<not_started>.*?);.*\
sport="(?P<sport>.*?)".*\
status="(?P<status>.*?)".*\
url="(?P<url>.*?)".*\n.*\
scoreOffer="(?P<score>.*?)".*', response.content.decode('unicode-escape'))
        if competition_name == 'CZ_TIPSPORT':
            icon_name = 'cz_tipsport_logo.png'
            minutes_enable_before_start = 60
        elif competition_name == 'SK_TIPSPORT':
            icon_name = 'sk_tipsport_logo.png'
            minutes_enable_before_start = 15
        else:
            icon_name = None
            minutes_enable_before_start = 60
        matches = [Match(name=match.group('name'),
                         competition=match.group('competition'),
                         sport=match.group('sport'),
                         url=match.group('url'),
                         start_time=match.group('start_time'),
                         status=match.group('status'),
                         not_started=match.group('not_started'),
                         score=match.group('score'),
                         icon_name=icon_name,
                         minutes_enable_before_start=minutes_enable_before_start)
                   for match in matches_iter if match.group(2) in COMPETITIONS[competition_name]]
        return matches

    def get_response_dwr_get_stream(self, relative_url, c0_param1):
        try:
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
        except requests.ConnectTimeout, requests.ConnectionError:
            raise NoInternetConnectionsException()

    def get_hls_stream_from_dwr(self, relative_url):
        response = self.get_response_dwr_get_stream(relative_url, 'HLS')
        url = re.search('value:"(.*?)"', response.text)
        if not url:
            raise UnableGetStreamMetadataException()
        return self.get_hls_stream(url.group(1))

    def get_hls_stream_from_page(self, page):
        try:
            next_hop = re.search('<iframe src="(.*?embed.*?)"', page)
            if not next_hop:
                raise UnableGetStreamMetadataException()
            page = self.session.get(next_hop.group(1))
            next_hop = re.search('"hls": "(.*?)"', page.text)
            if not next_hop:
                raise UnableGetStreamMetadataException()
            return self.get_hls_stream(next_hop.group(1))
        except requests.ConnectTimeout, requests.ConnectionError:
            raise NoInternetConnectionsException()

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

    def get_hls_stream(self, url):
        try:
            next_page = self.session.get(url)
            if 'm3u8' not in next_page.text:
                raise StreamHasNotStarted()
            playlists = [playlist for playlist in next_page.text.split('\n') if not playlist.startswith('#')]
            playlists = [playlist for playlist in playlists if playlist != '']
            playlist_relative_link = self.__select_stream_by_quality(playlists)
            playlist = url.replace('playlist.m3u8', playlist_relative_link)
            return HLSStream(playlist)
        except requests.ConnectTimeout, requests.ConnectionError:
            raise NoInternetConnectionsException()

    def get_rtmp_stream(self, relative_url):
        try:
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
                url = self.__select_stream_by_quality(urls)
                return parse_stream_dwr_response('"RTMP_URL":"{url}"'.format(url=url))
            else:
                response_url = re.search('value:"(.*?)"', response.text)
                url = response_url.group(1)
                response = self.session.get(url)
                stream = parse_stream_dwr_response(response.text)
                return stream
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()

    def get_stream(self, relative_url):
        """Get instance of Stream class from given relative link"""
        try:
            if not self.logged_in:
                self.login()
            stream_url = 'https://www.tipsport.cz/live' + relative_url
            page = self.session.get(stream_url)
            stream_content = re.search(
                '<div id="contentStream" class="(?P<stream_class>.*?)" data-stream="(?P<stream_type>.*?)">', page.text)
            if stream_content:
                stream_type = stream_content.group('stream_type')
                stream_class = stream_content.group('stream_class')
                if stream_class != stream_type:
                    message = self.get_alert_message(page.text)
                    raise TipsportMsg(message) if message else TipsportMsg()
                if stream_type == 'LIVEBOX_ELH':
                    return self.get_rtmp_stream(relative_url)
                elif stream_type == 'MANUAL':
                    return self.get_hls_stream_from_page(page.text)
                elif stream_type == 'HUSTE':
                    return self.get_hls_stream_from_dwr(relative_url)
                else:
                    raise UnableGetStreamMetadataException()
            else:
                raise UnableGetStreamMetadataException()
        except requests.ConnectionError, requests.ConnectTimeout:
            raise NoInternetConnectionsException()

    @staticmethod
    def get_alert_message(page_text):
        section = re.findall('<div id="contentStream.*?</div>', page_text, re.DOTALL)
        if len(section) == 0:
            return None
        alert_message = re.search('<div class="msg">(<p>)?(?P<msg>.*?)(</p>)?</div>', section[0])
        return alert_message.group('msg') if alert_message else None


def generate_random_number(length):
    """Generate string with given length that contains random numbers"""
    result = ''.join(random.SystemRandom().choice('0123456789') for _ in range(length))
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
    tokens = relative_url.split('/')
    number = tokens[2]
    try:
        int(number)
    except ValueError:
        raise UnableGetStreamNumberException()
    return number
