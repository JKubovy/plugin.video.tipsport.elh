# coding=utf-8
import re
import random
import json
import requests
import urllib
import time
import xml.etree.ElementTree
from .tipsport_exceptions import *
from .quality import Quality
from .site import Site
from .match import Match
from .stream import PlainStream, RTMPStream
from .utils import log, get_session_id_from_page
from .stream_strategy_factory import StreamStrategyFactory


COMPETITIONS = {
    'CZ_TIPSPORT': [u'Česká Tipsport extraliga', u'Tipsport extraliga', u'CZ Tipsport extraliga'],
    'SK_TIPSPORT': [u'Slovenská Tipsport liga', u'Slovensk\u00E1 Tipsport liga', u'Tipsport Liga', u'Slovenská extraliga'],
    'CZ_CHANCE': [u'Česká Chance liga', u'CZ Chance liga']
}
COMPETITION_LOGO = {
    'CZ_TIPSPORT': 'cz_tipsport_logo.png',
    'SK_TIPSPORT': 'sk_tipsport_logo.png',
    'CZ_CHANCE': 'cz_chance_liga_logo.png'
}

AGENT = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36 OPR/42.0.2393.137"


class Tipsport:
    """Class providing communication with Tipsport site"""
    def __init__(self, user_data, clean_function=None):
        self.session = requests.session()
        self.logged_in = False
        self.user_data = user_data
        self.stream_strategy_factory = StreamStrategyFactory(self.session, self.user_data)
        if clean_function is not None:
            clean_function()

    def login(self):
        """Login to mobile tipsport site with given credentials"""
        _ = self.session.get(self.user_data.site)  # load cookies
        payload = {
            'agent': AGENT,
            'requestURI': '/',
            'fPrint': 'unknown', # _generate_random_number(),
            'originalBrowserUri': '/',
            'userName': self.user_data.username,
            'password': self.user_data.password
        }
        try:
            self.session.post(self.user_data.site + '/LoginAction.do', payload)  # actual login
        except Exception as e:
            raise e.__class__  # remove tipsport account credentials from traceback
        # self._try_update_session_XAuthToken()
        if not self.is_logged_in():
            raise LoginFailedException()

    def is_logged_in(self):
        """Check if login was successful"""
        response = self.session.put(self.user_data.site_mobile + '/rest/ver1/client/restrictions/login/duration')
        if response.status_code == requests.status_codes.codes['OK']:
            log('Is logged in')
            return True
        log('Is logged out')
        return False

    def get_list_elh_matches(self, competition_name):
        """Get list of all available ELH matches on tipsport site"""
        response = self._get_matches_both_menu_response()
        data = json.loads(response.text)
        icon_name = COMPETITION_LOGO.get(competition_name)
        if competition_name in COMPETITIONS:
            matches_data = [match for sports in data['program'] if sports['id'] == 23
                            for matchesInTimespan in sports['matchesByTimespans']
                            for match in matchesInTimespan if match['competition'] in COMPETITIONS[competition_name]]
        else:
            matches_data = [match for sports in data['program']
                            for matchesInTimespan in sports['matchesByTimespans']
                            for match in matchesInTimespan]
        matches = [Match(name=match['name'],
                         competition=match['competition'],
                         sport=match['sport'],
                         url=match['url'],
                         start_time=match['matchStartTime'],
                         status=match['score']['statusOffer'],
                         not_started=not match['live'],
                         score=match['score']['scoreOffer'],
                         icon_name=icon_name,
                         minutes_enable_before_start=15) for match in matches_data]
        matches.sort(key=lambda match: match.match_time)
        log('Matches {0} loaded'.format(competition_name))
        return matches

    def get_stream(self, relative_url):
        """Get instance of Stream class from given relative link"""
        self._relogin_if_needed()
        self._check_alert_message_and_throw_exception()
        strategy = self.stream_strategy_factory.get_stream_strategy(relative_url)
        try:
            stream = strategy.get_stream(self.user_data.quality)
        except:
            raise UnableParseStreamMetadataException()
        if not stream:
            raise UnsupportedFormatStreamMetadataException()
        return stream

    def _relogin_if_needed(self):
        if not self.is_logged_in():
            self.login()

    def _try_update_session_XAuthToken(self):
        page = self.session.get(self.user_data.site_mobile)
        token = get_session_id_from_page(page.text)
        if token:
            self.session.headers.update({'X-Auth-Token': token})
        else:
            log('try_update_session_XAuthToken: token not found')

    def _get_matches_both_menu_response(self):
        """Get dwr respond with all matches today"""
        self._relogin_if_needed()
        # response = self.session.get(self.user_data.site_mobile + '/rest/articles/v1/tv/program?columnId=23&day=0&countPerPage=1')
        response = self.session.get(self.user_data.site_mobile + '/rest/articles/v1/tv/program?day=0&articleId=')
        response.encoding = 'utf-8'
        if 'program' not in response.text:
            log(response.text)
            raise UnableGetStreamListException()
        return response

    def _get_response_dwr_get_stream(self, relative_url, c0_param1):
        stream_url = self.user_data.site + '/live' + relative_url
        page = self.session.get(stream_url)
        token = get_token(page.text)
        relative_url = relative_url.split('#')[0]
        dwr_script = self.user_data.site + '/dwr/call/plaincall/StreamDWR.getStream.dwr'
        payload = {
            'callCount': 1,
            'page': relative_url,
            'httpSessionId': '',
            'scriptSessionId': token,
            'c0-scriptName': 'StreamDWR',
            'c0-methodName': 'getStream',
            'c0-id': 0,
            'c0-param0': 'number:{0}'.format(get_stream_number(relative_url)),
            'c0-param1': 'string:{0}'.format(c0_param1),
            'batchId': 9
        }
        response = self.session.post(dwr_script, payload)
        return response

    def _get_hls_stream_from_dwr(self, relative_url):
        response = self._get_response_dwr_get_stream(relative_url, 'HLS')
        url = re.search('value:"(.*?)"', response.text)
        if not url:
            raise UnableGetStreamMetadataException()
        return self._get_hls_stream(url.group(1))

    def _get_hls_stream_from_page(self, page):
        next_hop = re.search('<iframe src="(.*?embed.*?)"', page)
        if not next_hop:
            raise UnableGetStreamMetadataException()
        page = self.session.get(next_hop.group(1))
        next_hop = re.search('"hls": "(.*?)"', page.text)
        if not next_hop:
            raise UnableGetStreamMetadataException()
        return self._get_hls_stream(next_hop.group(1))

    def _select_stream_by_quality(self, list_of_streams):
        """List is ordered from the lowest to the best quality"""
        if len(list_of_streams) <= 0:
            raise UnableGetStreamMetadataException('List of streams by quality is empty')
        if len(list_of_streams) > self.user_data.quality:
            return list_of_streams[self.user_data.quality]
        if self.user_data.quality in [Quality.LOW, Quality.MID]:
            return list_of_streams[0]
        return list_of_streams[-1]

    def _get_hls_stream(self, url, reverse_order=False):
        url = url.replace('\\', '')
        response = self.session.get(url)
        if 'm3u8' not in response.text:
            raise StreamHasNotStarted()
        playlists = [playlist for playlist in response.text.split('\n') if not playlist.startswith('#')]
        playlists = [playlist for playlist in playlists if playlist != '']
        if reverse_order:
            playlists.reverse()
        playlist_relative_link = self._select_stream_by_quality(playlists)
        playlist = url.replace('playlist.m3u8', playlist_relative_link)
        return PlainStream(playlist)

    def _get_rtmp_stream(self, relative_url):
        response = self._get_response_dwr_get_stream(relative_url, 'SMIL')
        search_type = re.search('type:"(.*?)"', response.text)
        response_type = search_type.group(1) if search_type else 'ERROR'
        if response_type == 'ERROR':  # use 'string:RTMP' instead of 'string:SMIL'
            response = self._get_response_dwr_get_stream(relative_url, 'RTMP')
        search_type = re.search('type:"(.*?)"', response.text)
        response_type = search_type.group(1) if search_type else 'ERROR'
        if response_type == 'ERROR':  # StreamDWR.getStream.dwr not working on this specific stream
            raise UnableGetStreamMetadataException()
        if response_type == 'RTMP_URL':
            if re.search('value:"?(.*?)"?}', response.content.decode('unicode-escape')).group(1).lower() == 'null':
                raise UnableGetStreamMetadataException()
            urls = re.findall('(rtmp.*?)"', response.content.decode('unicode-escape'))
            urls.reverse()
            urls = [url.replace(r'\u003d', '=') for url in urls]
            urls = [url.replace('\\', '') for url in urls]
            url = self._select_stream_by_quality(urls)
            return _parse_stream_dwr_response('"RTMP_URL":"{url}"'.format(url=url))
        else:
            response_url = re.search('value:"(.*?)"', response.text)
            url = response_url.group(1)
            url = url.replace('\\', '')
            response = self.session.get(url)
            stream = _parse_stream_dwr_response(response.text)
            return stream

    def _check_alert_message_and_throw_exception(self):
        """
        Return any alert message from Tipsport (like bet request)
        Return None if everything is OK
        """
        page = self.session.get(self.user_data.site_mobile + '/rest/articles/v1/tv/info')
        name = 'buttonDescription'
        try:
            data = json.loads(page.text)
            if name not in data:
                raise TipsportMsg()
            text = data[name]
            if text is None:
                return None
            raise TipsportMsg(text.split('.')[0] + '.')
        except TypeError:
            log('Unable to get Tipsport alert message')
            raise UnableGetStreamMetadataException()

    @staticmethod
    def _parse_stream_info_response(response):
        data = json.loads(response.text)
        if data['displayRules'] is None:
            raise (TipsportMsg(data['data']))
        # if data['returnCode']['name'] == 'NOT_STARTED':
        #     raise StreamHasNotStarted()
        stream_source = data['source']
        stream_type = data['type']
        if stream_source is None or stream_type is None:
            raise UnableGetStreamMetadataException()
        return stream_source, stream_type, data['data']

    def _get_stream_source_type_and_data(self, relative_url):
        """Get source and type of stream"""
        stream_number = get_stream_number(relative_url)
        base_url = self.user_data.site_mobile + '/rest/offer/v2/live/matches/{stream_number}/stream?deviceType=DESKTOP'.format(
            stream_number=stream_number)
        url = base_url + '&format=HLS'
        response = self.session.get(url)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if 'auth=' not in data:
                url = base_url + '&format=RTMP'
                response = self.session.get(url)
                stream_source, stream_type, data = self._parse_stream_info_response(response)
            return stream_source, stream_type, data
        except (TypeError, KeyError):
            raise UnableGetStreamMetadataException()


def _generate_random_number():
    """Generate string with given length that contains random numbers"""
    result = ''.join(random.SystemRandom().choice('0123456789') for _ in range(10))
    result = result + '-' + ''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
    return result


def _parse_stream_dwr_response(response_text):
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
