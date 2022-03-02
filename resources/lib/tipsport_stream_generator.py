# coding=utf-8
import re
import time
import random
import json
import requests
from urllib import parse
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
COMPETITIONS_WITH_LOGOS = [item for sublist in COMPETITIONS.values() for item in sublist]
COMPETITION_LOGO = {
    'CZ_TIPSPORT': 'cz_tipsport_logo.png',
    'SK_TIPSPORT': 'sk_tipsport_logo.png',
    'CZ_CHANCE': 'cz_chance_liga_logo.png'
}

AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36 OPR/83.0.4254.27"


class Tipsport:
    """Class providing communication with Tipsport site"""
    def __init__(self, user_data, clean_function=None):
        self.session = requests.session()
        self._set_session_headers()
        self.logged_in = False
        self.user_data = user_data
        self.stream_strategy_factory = StreamStrategyFactory(self.session, self.user_data)
        if clean_function is not None:
            clean_function()

    def _set_session_headers(self):
        self.session.headers['User-Agent'] = AGENT
        self.session.headers['DNT'] = '1'
        self.session.headers[
            'jATVGpTmOw-f'] = 'A8WpVEl_AQAARhO-WwCyRZ-LXgXD9luBsuGI516WPNDrq1t7tvgRukXwMG48AU5mHEScuN61wH8AADQwAAAAAA=='
        self.session.headers['jATVGpTmOw-b'] = '-awi24f'
        self.session.headers['jATVGpTmOw-c'] = 'AEA6Ukl_AQAArSgfcsTalE7ErbBPDXonh1hNsf0_9nFpM9DvscUVk40kQKOs'
        self.session.headers[
            'jATVGpTmOw-d'] = 'ABaChIjBDKGNgUGAQZIQhISi0eIApJmBDgDFFZONJECjrAAAAAA0OShlAHwiVtAtQhKJEYFKBssnxbY'
        self.session.headers['jATVGpTmOw-z'] = 'q'
        self.session.headers[
            'jATVGpTmOw-a'] = 'u4evBvs-B-40Pe0A8bvcExwyOU7TmYI_2Zu2oc3A_NK2xMFO6HWE4PdD1Hp_X_0Vj=RzbtT_vl_LCwzB_FefQkW6o4uw7Mv-MZK0S3DCBgIA-HkfZLGSA5C-UZC38UJP=Y2JYg=_YLex4zNjjt5D=Kr=23xjzU8OQfmlAdJmuU-x7BQDjYjOXYzWDLN3WFdDIqMunmlq-sVvu26sso8v5nMUqpqDRLjQyffNfu7cxHPbunl3Y0ZqODtYwoMW2WV2m-7pWRq3hHk=F1hZVwKVQIK=XAX0RCEvwAEmfdkDwu1vj5dwpJow7nlqypuctyQM81rr8Ti1c7i7fIyvwuJCftUu_umx=Rcd=mPpb2_ievYLkI2sw-gpJMzrtPTV3GGedr7UiRSG6bfW44UTMgq-O3VMwQsYUwFRZDT1kcvtx6nPUEAIqczic5xniOX8VH2nVRQEBF52UsIrl0lbKsJpjzXKqpSaTOdtRZxzYmVxSI3kBrMV5FzOcYcQs4VvHn4ctcDbca2D4eo7McSwCbdyKFuMGYk5rSOHJEOiZVumjB8SI1w-r8SRq6Z0V7TNb0gIKizqkcieVNzkGwmw0sF4fC4mXAT2q6cyInv-fryQTDuIceVLhDE4_bSSL2ckrRFXuGBtXtif5TkwMtQLEAJ=OEvzs27x6p6EPJ80mx7HN_Bahr_TKluev5=U7gv6h3oYubcNGty8JF1R1=mWw1ATVL1lZAgvxcp0NheFBGJWeSUNqIQT8UC=XJNjkkCyNmArr7L5V_pn6Pm61Y0KT4kMjtWCYOtQ0COm8nyg=gpdco3axpzLjS=rR7hVqdbx8-u6zZXGuKv=RS4KWTT8dEBhp3l7NLYHe_xGevjVw1eV6NNC2XnXU680t56HJaemXOPZLKoAm4gX28oL6Jq8DAr5gCA3qCCdmEROiIjEp=OTu7RTueG7aoDfwVPyiuGTUEuSD5TxhjjY8NUjW80_nDlN2MDzCE8z_2pJf-w7Q-MQE701VSLaNtlYf=Cmeq8pKVDV_iH0oMinSgyBBurfDbR-0jLOiMtlp3CZPCvXs0fNYpPBF_0YeOyRNeB=cArUw1WmqMeli0DuAKD5GYZQ0hmEBeIO66fyHARtFlS5BLS=AEqbEOg4_14vlswB7tYm-5kTzm61dqn=R1KZTqajljCV0tLxxgWUwqRqYkvM7gEZZsE-nY_MuCw1K1EMBM4XHk=uogVts202t7JQFIIuPql0PBlqeVa=jxTbylYlE-RvGkq1Jc57E1X4oOHy1OLqziUpmSC84RdYzLSZqXLgOBx8Dg_Xx00BYu8w4-fRYuoCX4rYW_fsIYaMnR5J3Oe-XtsaRGg6vtD8DCmWkJNuOckaQ-zZ8C1x8PZC5g8TicQAjmD0lHSgOkZRGglzsHP63G8AwaFXF3kUpIYaom1HisfTgmZk5HYe=lteBPPqgdn6-UTI7gwpO==x6DQl_ciiO7WXq6Eh4Jijr3yt2xRdtQ4s-xaQrV-Sxu7JvBaCt7OyPALnaBfRjRUggUcVqDxOIBgbiZDmMopbFN767hlVMV2HoNNFJns0WEOy55Ejzhag0X=ACOWJwBHp0zvqUuvu=wM7bRS0YY=MMsUrEpoe2E=oncmvMwwYSlX8mbP5kg3jk-Sq6mZq5_V-zXHnF1zsVZYcGNy87dfTAM-sTogUNVUuJDjWa3xMiZ_7AiemDGfULxHIFc1-ZM=1vYghUV0tvZvzLOb1k4G-d5JJJ-aUrfWUfjVXjY1=Ut83RCw7L36VYb74IAUHX54nsbyZtvfoE62T6Rfk0sKzrBP4TSBBVuds_=1XCZwLj7S7E5YUKr-ayrctXoV0hJ_IMMJOK=IVSX5_qfA8LdQMUf=0GY=pIspWvIOXtqAbSE_5wkVNBkkwQVqTkRhCH2CZR1d2AMISR4868PTVQOBhiOp2p=EVmNTL7-nd3xI_8vOjfgPvRnZaADgbbCatfQKZvWuYvcAjS=UJTNz2BYZTn2VVGjIhtagHCxMR-xRXcw4anDMSls=T6NHnjivZ4kfLGNtJQWYWgvrsd74n6VRPyi_IP=8Iw_8nrl515zSoYDb2=mFEuNXzDJVND0sE8pWEtskdv5nULmGuI=UfEBUiCaTQi6Pl3vxqsPIcnhHBsC_4SiwGKHVRGMrxzJNKNiZBRcWsCBvlgW3JqjwXAH4M_r73faPDt1QTQSKng-CngJ24TVOTHcCakcM0qAAPYmM8X=3e7-RXnEGjhkzd8HdrzIsIBeXzPgZdaEjVpP6AoyUrN6Q7SZpkhu-qoi2s0HmTYfSHvFaeiMYG3D50iDrHJ7O4xSW=UU1u4GP=SDf5coPKdxihT2YclFR2ifr_Yq7bsJM8uHxm=dDys1JmqBg6eHRgqD6LmlJQptoOmLHbhm6KcREeL4KR2qXmZapWwIHwjjElyYgY_8Qd3JbIny6Wq6yq4u6qVO0nYC_QQSQnreuwZiG=rdIaXDeBdwWCxv8l81BYzZ8zPLsGgaxarl0OEyODE7nP=BgMX4ohz0U2Asnynq-HiYuZTSCurHrGRNYUzpd-Bi7qrKSNpf6LIqaXkKzG3KfgZOSoDexB4JCaVmgc07YXW1KMzZjq87OeALWMz_hPw5=mf1tP0AYT3tOumu16P7B5paUY3nQg0K17kV1Dn711NgTff8bH5OAXkWtei4e4s8KqwHDv1fbtlYA0LSMJjJ3SPlOu-cDESxQnopNBu3cfbYKcgd-b7RGCmCcQHTMMt-2r7_f7u5Y2sc8Qox5FZy4rurdPMM_dgPm3oxg7MbvamiYy-T1JCB3=RegSDnve7UtTf6IpfcQRpzWUQxBTozVHnNRrzLPsxxTe0yOHeOot3j7_L_tgBQj8bGynhud1botB0hfpuMtH1-3t_eocJ-wEz477WoiH6gM1wfJZV36ciu4rPxDJo2Gc81yX=daUIjX5BeaOPRchI0QQtHXi0BKxKKT5mtlCE6TlcRsDyRjbOf0iNpYJNdmjRWEi87PkMCEGCjIizgxTj=xZRgLvaUWR8siXJkvEaA3J-Xzf-vxqW2-dmlFm3wuoJfcDi5sTOMy4YqTqcxui47sA=UzkM0jxcI=gsbyShva0pgFKJATJenJKVUXD2PTiCFQeYprAjkBNXDOgKkZ8MHeOIB05mGcw4aFk7Z1u6zYlM5LjOqlF4bxxCd3K6kloQIE2XfJJ_nOXL-S8PTL2FxIX_5S-lRd7_UF85Q55BaFHUcrzFbEup5bq3e3qU30kcsM4QgyXhpYRyS_Ye=MRv1Lhauco6xObW0uNs11uMnQl5zGRZqnsUydbkrl_qf7dvHektPHw34Ludna-O_yCbFpVbLXXZx-okHC534Wn3J3=GH7FQcWU4_esAw-kEYHdTw=KFLQR2mc8AFT=8a5HqH7tgTjs_34XDypXSna1qBQDzikeJWucSEUqRbLgVHlOUakeOeDZpjhBHEo77Dc0UzrM5lfZULV3LmaHnP=tLtlK4bcs=1MHAKLhp2envCyh6qE4haf5sIbq_XnEs8iB2qZwk-fb6oU7bP6HIWJJhDDI-45NVGdIU2321DIWIIs5-B58mHWpNiQWAW=PqJ70We4=yLlP8TPBLYDZZGX_Ty=XuJoDxxAMPr4Esd8fBPMja=mqrDSfrwrcrVc_T5xG=hfOFZNBO-wAeTjEjuj72fHHc8rcc=Dz58vEHQtShC6WdRWgSwGpyq-BZnCB1gvm4Z_z8AKn3YLh7kAK'

    def login(self):
        """Login to mobile tipsport site with given credentials"""
        self.session.get(self.user_data.site)  # load cookies
        url = self.user_data.site + '/rest/client/v4/session'
        payload = {'password': self.user_data.password, 'username': self.user_data.username}
        time.sleep(1.3)  # Wait some tome to next request to prevent suspicion that it is automated
        try:
            self.session.post(url, json=payload)  # actual login
        except Exception as e:
            raise e.__class__  # remove tipsport account credentials from traceback
        # self._try_update_session_XAuthToken()
        if not self.is_logged_in():
            raise Exceptions.LoginFailedException()

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
