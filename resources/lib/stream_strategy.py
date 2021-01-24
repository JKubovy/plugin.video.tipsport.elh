import re
import json
try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin
from .utils import log
from .stream import RTMPStream, PlainStream
from .tipsport_exceptions import UnableGetStreamMetadataException


class RTMPStreamStrategy:
    def __init__(self, url):
        self._url = url

    def get_stream(self):
        try:
            playpath = (self._url.split('/'))[-1]
            url = self._url.replace('/' + playpath, '')
            tokens = url.split('/')
            app = '/'.join([tokens[-2], tokens[-1]])
            return RTMPStream(url, playpath, app, True)
        except IndexError:
            return None


class UrlImgStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self):
        hls_data = self._session.get(self._url)
        data = json.loads(hls_data.content)
        attribute_name = 'hlsUrl'
        if attribute_name not in data or data[attribute_name] is None:
            return None
        m3u8_playlist_url = data[attribute_name]
        stream_url = m3u8_playlist_url
        return PlainStream(stream_url)


class HLSStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self):
        url_query = _get_query_part(self._url)
        stream_url = self._url
        if url_query:
            if '?' in stream_url:
                stream_url = stream_url.strip() + '&' + url_query
            else:
                stream_url = stream_url.strip() + '?' + url_query
        stream_url = stream_url.strip()
        return PlainStream(stream_url)


class UrlPerformeStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self):
        xml_data = self._session.get(self._url)
        possible_m3u8_urls = re.findall('<streamLaunchCode><!\[CDATA\[(.*)\]\]></streamLaunchCode>', xml_data.text.replace('\n', ''))
        possible_m3u8_urls = [m3u8_url for m3u8_url in possible_m3u8_urls if 'm3u8' in m3u8_url or 'hls' in m3u8_url]
        if len(possible_m3u8_urls) == 0:
            return None
        stream_url = self._url
        return PlainStream(stream_url)


class UrlAguraStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self):
        stream_url = self._url
        return PlainStream(stream_url)


class TvComStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self):
        stream_url = self._url
        return PlainStream(stream_url)


class NoneStrategy:
    def __init__(self, relative_url):
        self.relative_url = relative_url

    def get_stream(self):
        log('NoneStrategy: ' + self.relative_url)
        return None


def _is_stream_relative(stream_url):
    if stream_url.startswith('http'):
        return False
    if stream_url.startswith('.'):
        return True
    if stream_url.startswith('/'):
        return True
    tokens = stream_url.split('.')
    if len(tokens) >= 2 and tokens[1].startswith('m3u8'):
        return True
    return True


def _get_query_part(url):
    if '?' not in url:
        return None
    query_part = url.split('?')[1]
    if len(query_part) == 0:
        return None
    return query_part
