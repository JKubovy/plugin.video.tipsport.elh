# coding=utf-8
import re
import random
import json
import requests
from . import tipsport_exceptions as Exceptions
from .match import Match
from .utils import log, get_session_id_from_page
from .stream_strategy_factory import StreamStrategyFactory

COMPETITIONS = {
    'CZ_TIPSPORT': [u'Česká Tipsport extraliga', u'Tipsport extraliga', u'CZ Tipsport extraliga'],
    'SK_TIPSPORT':
    [u'Slovenská Tipsport liga', u'Slovensk\u00E1 Tipsport liga', u'Tipsport Liga', u'Slovenská extraliga'],
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
        self.session.get(self.user_data.site)  # load cookies
        payload = {
            'agent': AGENT,
            'requestURI': '/',
            'fPrint': _generate_random_number(),
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
            raise Exceptions.LoginFailedException()

    def is_logged_in(self):
        """Check if login was successful"""
        response = self.session.put(self.user_data.site_mobile + '/rest/ver1/client/restrictions/login/duration')
        if response.status_code == requests.status_codes.codes['OK']:
            log('Is logged in')
            return True
        log('Is logged out')
        return False

    def get_list_matches(self, competition_name):
        """Get list of all available ELH matches on tipsport site"""
        response = self._get_matches_both_menu_response()
        data = json.loads(response.text)
        icon_name = COMPETITION_LOGO.get(competition_name)
        if competition_name in COMPETITIONS:
            matches_data = [
                match for sports in data['program'] if sports['id'] == 23
                for matchesInTimespan in sports['matchesByTimespans'] for match in matchesInTimespan
                if match['competition'] in COMPETITIONS[competition_name]
            ]
        else:
            matches_data = [
                match for sports in data['program'] for matchesInTimespan in sports['matchesByTimespans']
                for match in matchesInTimespan
            ]
        matches = [
            Match(name=match['name'],
                  competition=match['competition'],
                  sport=match['sport'],
                  url=match['url'],
                  start_time=match['matchStartTime'],
                  status=match['score']['statusOffer'],
                  not_started=not match['live'],
                  score=match['score']['scoreOffer'],
                  icon_name=icon_name,
                  minutes_enable_before_start=15) for match in matches_data
        ]
        matches.sort(key=lambda match: match.match_time)
        log('Matches {0} loaded'.format(competition_name))
        return matches

    def get_stream(self, relative_url):
        """Get instance of Stream class from given relative link"""
        self._relogin_if_needed()
        self._check_alert_message_and_throw_exception()
        strategy = self.stream_strategy_factory.get_stream_strategy(relative_url)
        try:
            stream = strategy.get_stream()
        except:
            raise Exceptions.UnableParseStreamMetadataException()
        if not stream:
            raise Exceptions.UnsupportedFormatStreamMetadataException()
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
            raise Exceptions.UnableGetStreamListException()
        return response

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
                raise Exceptions.TipsportMsg()
            text = data[name]
            if text is None:
                return None
            raise Exceptions.TipsportMsg(text.split('.')[0] + '.')
        except TypeError:
            log('Unable to get Tipsport alert message')
            raise Exceptions.UnableGetStreamMetadataException()


def _generate_random_number():
    """Generate string with given length that contains random numbers"""
    result = ''.join(random.SystemRandom().choice('0123456789') for _ in range(10))
    result = result + '-' + ''.join(random.SystemRandom().choice('0123456789abcdef') for _ in range(32))
    return result


def get_token(page):
    """Get scriptSessionId from page for proper DWRScript call"""
    token = re.search('JAWR.dwr_scriptSessionId=\'([0-9A-Z]+)\'', page)
    if token is None:
        raise Exceptions.UnableDetectScriptSessionIdException()
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
        raise Exceptions.UnableGetStreamNumberException()
    return number
