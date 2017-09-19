import re
import random
import requests
import urllib
from datetime import datetime, timedelta
from tipsport_exceptions import *


class Match:
    """Class represents one match with additional information"""

    def __init__(self, name, competition, sport, url, start_time, status, not_started, score):
        self.name = name
        self.competition = competition
        self.sport = sport
        self.url = url
        self.start_time = start_time
        self.status = status
        self.started = True if not_started == 'false' else False
        self.score = score

    def is_stream_enabled(self):
        hours_before_start = 1
        now = datetime.now()
        match_time = datetime.strptime(self.start_time, '%H:%M')
        time_to_start = match_time - now
        return time_to_start.seconds < timedelta(hours=hours_before_start).seconds


class Stream:
    """Class represent one stream and store metadata used to generate stream link"""

    def __init__(self, rtmp_url, playpath, app, live_stream):
        self.rtmp_url = rtmp_url
        self.playpath = playpath
        self.app = app
        self.live_stream = live_stream

    def get_rtmp_link(self):
        return '{rtmp_url} playpath={playpath} app={app}{live}'.format(rtmp_url=self.rtmp_url,
                                                                       playpath=self.playpath,
                                                                       app=self.app,
                                                                       live=' live=true' if self.live_stream else '')


class Tipsport:
    """Class providing communication with Tipsport.cz site"""

    def __init__(self, username, password):
        self.session = requests.session()
        self.logged_in = False
        self.username = username
        self.password = password

    def login(self):
        """Login to https://www.tipsport.cz site with given credentials"""
        agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 " \
                "Safari/537.36 OPR/42.0.2393.137 "
        self.session.get('https://www.tipsport.cz/')  # load cookies
        payload = {'agent': agent,
                   'requestURI': '/',
                   'fPrint': generate_random_number(10),
                   'userName': self.username,
                   'password': self.password}
        try:
            self.session.post('https://www.tipsport.cz/LoginAction.do', payload)  # actual login
        except Exception as e:
            raise e.__class__   # remove tipsport account credentials from traceback
        self.check_login()

    def check_login(self):
        """Check if login to https://www.tipsport.cz was successful"""
        page = self.session.get('https://www.tipsport.cz/')
        if 'LogoutAction.do' not in page.text:
            raise LoginFailedException()
        self.logged_in = True

    def get_list_elh_matches(self):
        """Get list of all available ELH matches on https://www.tipsport.cz/tv"""
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
                       'c0-param3': 'string:COMPETITION_SPORT',
                       'batchId': 2}
            response = self.session.post(dwr_script, payload)
            response.encoding = 'utf-8'
            matches_iter = re.finditer('.*\
abbrName="(?P<name>.*?)".*\
competition="(?P<competition>.*?)".*\
dateStartAsHHMM="(?P<start_time>.*?)".*\
notStarted=(?P<not_started>.*?);.*\
sport="(?P<sport>.*?)".*\
status="(?P<status>.*?)".*\
url="(?P<url>.*?)".*\n.*\
scoreOffer="(?P<score>.*?)".*', response.content.decode('unicode-escape'))
            matches = [Match(match.group('name'),
                             match.group('competition'),
                             match.group('sport'),
                             match.group('url'),
                             match.group('start_time'),
                             match.group('status'),
                             match.group('not_started'),
                             match.group('score'))
                       for match in matches_iter if match.group(2) in ['Tipsport extraliga', 'CZ Tipsport extraliga']]
            return matches
        except requests.exceptions.ConnectionError:
            raise NoInternetConnectionsException()

    def get_stream(self, relative_url):
        """Get instance of Stream class from given relative link"""
        try:
            if not self.logged_in:
                self.login()
            stream_url = 'https://www.tipsport.cz/live' + relative_url
            page = self.session.get(stream_url)
            token = get_token(page.text)
            relative_url = relative_url.split('#')[0]
            dwr_script = 'https://www.tipsport.cz/dwr/call/plaincall/StreamDWR.getStream.dwr'
            number = 'number:' + get_stream_number(relative_url)
            payload = {'callCount': 1,
                       'page': relative_url,
                       'httpSessionId': '',
                       'scriptSessionId': token,
                       'c0-scriptName': 'StreamDWR',
                       'c0-methodName': 'getStream',
                       'c0-id': 0,
                       'c0-param0': number,
                       'c0-param1': 'string:SMIL',
                       'batchId': 9}
            response = self.session.post(dwr_script, payload)
            response_type = re.search('type:"(.*?)"', response.text).group(1)
            if response_type == 'ERROR':  # use 'string:RTMP' instead of 'string:SMIL'
                payload['c0-param1'] = 'string:RTMP'
                response = self.session.post(dwr_script, payload)
            response_type = re.search('type:"(.*?)"', response.text).group(1)
            if response_type == 'ERROR':  # StreamDWR.getStream.dwr not working on this specific stream
                raise UnableGetStreamMetadataException()
            if response_type == 'RTMP_URL':
                if re.search('value:"?(.*?)"?}', response.content.decode('unicode-escape')).group(1).lower() == 'null':
                    raise UnableGetStreamMetadataException()
                url = re.search('(rtmp.*?)"',
                                response.content.decode('unicode-escape')).group(1).replace(r'\u003d', '=')
                return parse_stream_dwr_response('"RTMP_URL":"{url}"'.format(url=url))
            else:
                response_url = re.search('value:"(.*?)"', response.text)
                url = response_url.group(1)
                response = self.session.get(url)
                stream = parse_stream_dwr_response(response.text)
                return stream
        except requests.exceptions.ConnectionError:
            raise NoInternetConnectionsException()


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
    return Stream(url, playpath, app, True)


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
