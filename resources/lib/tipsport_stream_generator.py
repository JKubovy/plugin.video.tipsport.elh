# coding=utf-8
import json
import requests
import pickle
from os import path, makedirs
from . import tipsport_exceptions as Exceptions
from .match import Match
from .utils import log, get_host_info
from .stream_strategy_factory import StreamStrategyFactory

COOKIES_FILENAME = 'session.cookies'

COMPETITIONS = {
    'CZ_TIPSPORT': [u'Česká Tipsport extraliga', u'Tipsport extraliga', u'CZ Tipsport extraliga'],
    'SK_TIPSPORT':
    [u'Slovenská Tipsport liga', u'Slovensk\u00E1 Tipsport liga', u'Tipsport Liga', u'Slovenská extraliga'],
    'CZ_CHANCE': [u'Česká Chance liga', u'CZ Chance liga']
}
COMPETITIONS_WITH_LOGOS = [item for sublist in COMPETITIONS.values() for item in sublist]
COMPETITION_LOGO = {
    'CZ_TIPSPORT': 'cz_tipsport_logo.png',
    'SK_TIPSPORT': 'sk_tipsport_logo.png',
    'CZ_CHANCE': 'cz_chance_liga_logo.png'
}

AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 OPR/83.0.4254.27"


class Tipsport:
    """Class providing communication with Tipsport site"""
    def __init__(self, kodi_helper, clean_function=None):
        self.session = self._get_session(kodi_helper)
        self.logged_in = False
        self.kodi_helper = kodi_helper
        self.user_data = kodi_helper.user_data
        self.lib_path = kodi_helper.lib_path
        self.stream_strategy_factory = StreamStrategyFactory(self.session, self.user_data)
        if clean_function is not None:
            clean_function()

    @staticmethod
    def _get_session(kodi_helper):
        session = requests.session()
        Tipsport._set_session_headers(session)
        cookie_path = path.join(kodi_helper.addon_data_path, COOKIES_FILENAME)
        if path.exists(cookie_path):
            with open(cookie_path, 'rb') as f:
                session.cookies.update(pickle.load(f))
        return session

    def save_session(self):
        try:
            cookie_path = path.join(self.kodi_helper.addon_data_path, COOKIES_FILENAME)
            makedirs(self.kodi_helper.addon_data_path, exist_ok=True)
            with open(cookie_path, 'wb') as f:
                log(f'cookie_path: {cookie_path}')
                pickle.dump(self.session.cookies, f)
        except FileNotFoundError:
            pass

    @staticmethod
    def _set_session_headers(session):
        session.headers['User-Agent'] = AGENT
        session.headers['DNT'] = '1'

    def _get_login_request(self):
        params = {
            'Addon': self.kodi_helper.plugin_name,
            'AddonVersion': self.kodi_helper.version,
            'RequestVersion': 1,
            'HostInfo': get_host_info()
        }
        lr_response = requests.post('https://tipsportloginprovider.azurewebsites.net/api/get_login_request',
                                    json=params)
        if not lr_response.ok:
            raise Exceptions.LoginFailedException()
        data = json.loads(lr_response.text)
        if (any([
                key not in data
                for key in ['version', 'url', 'post_data', 'username_keyword', 'password_keyword', 'headers']
        ])):
            raise Exceptions.LoginFailedException()
        if data['version'] != 1:
            raise Exceptions.NeedPluginUpdateException()

        post_data = json.loads(data['post_data'].replace(data['username_keyword'], self.user_data.username).replace(
            data['password_keyword'], self.user_data.password))
        headers = dict(data['headers'])
        preparedRequest = requests.Request("POST",
                                           data['url'],
                                           json=post_data,
                                           headers=headers,
                                           cookies=self.session.cookies)
        return preparedRequest.prepare()

    def login(self):
        """Login to mobile tipsport site with given credentials"""
        self.session.get(self.user_data.site)  # load cookies
        try:
            login_request = self._get_login_request()
            _ = self.session.send(login_request)
        except Exception as e:
            raise e.__class__  # remove tipsport account credentials from traceback
        if not self.is_logged_in():
            raise Exceptions.LoginFailedException()
        self.save_session()

    def is_logged_in(self):
        """Check if login was successful"""
        response = self.session.put(self.user_data.site + '/rest/ver1/client/restrictions/login/duration')
        if response.ok:
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
                  is_competition_with_logo=match['competition'] in COMPETITIONS_WITH_LOGOS,
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
        except Exception:
            raise Exceptions.UnableParseStreamMetadataException()
        if not stream:
            raise Exceptions.UnsupportedFormatStreamMetadataException()
        return stream

    def _relogin_if_needed(self):
        if not self.is_logged_in():
            self.login()

    def _get_matches_both_menu_response(self):
        """Get dwr respond with all matches today"""
        self._relogin_if_needed()
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
