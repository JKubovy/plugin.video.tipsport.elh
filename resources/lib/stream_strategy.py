import re
import json
try:
    from urlparse import urljoin
except:
    from urllib.parse import urljoin
from .utils import log
from .quality import Quality
from .stream import RTMPStream, PlainStream
from .tipsport_exceptions import UnableGetStreamMetadataException


class RTMPStreamStrategy:
    def __init__(self, url):
        self._url = url

    def get_stream(self, _):
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

    def get_stream(self, quality):
        hls_data = self._session.get(self._url)
        data = json.loads(hls_data.content)
        attribute_name = 'hlsUrl'
        if attribute_name not in data or data[attribute_name] is None:
            return None
        m3u8_playlist_url = data[attribute_name]
        m3u8_playlist = self._session.get(m3u8_playlist_url)
        stream_url = _get_stream_url_from_m3u8(m3u8_playlist, m3u8_playlist_url, quality)
        return PlainStream(stream_url)


class HLSStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self, quality):
        url_query = _get_query_part(self._url)
        m3u8_playlist = self._session.get(self._url)
        stream_url = _get_stream_url_from_m3u8(m3u8_playlist, self._url, quality)
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

    def get_stream(self, quality):
        xml_data = self._session.get(self._url)
        possible_m3u8_urls = re.findall('<streamLaunchCode><!\[CDATA\[(.*)\]\]></streamLaunchCode>', xml_data.text.replace('\n', ''))
        possible_m3u8_urls = [m3u8_url for m3u8_url in possible_m3u8_urls if 'm3u8' in m3u8_url or 'hls' in m3u8_url]
        if len(possible_m3u8_urls) == 0:
            return None
        m3u8_playlist = self._session.get(possible_m3u8_urls[-1])
        stream_url = _get_stream_url_from_m3u8(m3u8_playlist, self._url, quality)
        return PlainStream(stream_url)


class UrlAguraStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self, quality):
        json_data_response = self._session.get(self._url)
        json_data = json.loads(json_data_response.text)
        m3u8_playlist = self._session.get(json_data['url'])
        stream_url = _get_stream_url_from_m3u8(m3u8_playlist, self._url, quality)
        return PlainStream(stream_url)


class TvComStreamStrategy:
    def __init__(self, session, url):
        self._url = url
        self._session = session

    def get_stream(self, quality):
        json_data_response = self._session.get(self._url)
        json_data = json.loads(json_data_response.text)
        m3u8_playlist = self._session.get(json_data['url']['hls']['url'])
        stream_url = _get_stream_url_from_m3u8(m3u8_playlist, self._url, quality)
        return PlainStream(stream_url)


class NoneStrategy:
    def __init__(self, relative_url):
        self.relative_url = relative_url

    def get_stream(self, _):
        log('NoneStrategy: ' + self.relative_url)
        return None


def _select_stream_by_quality(list_of_streams, quality):
    """List is ordered from the lowest to the best quality"""
    if len(list_of_streams) == 0:
        log('list_of_streams is empty')
        raise UnableGetStreamMetadataException('List of streams by quality is empty')
    if len(list_of_streams) == quality + 1:
        return list_of_streams[quality]
    if quality in [Quality.LOW, Quality.MID]:
        return list_of_streams[0]
    return list_of_streams[-1]


def _get_stream_url_from_m3u8(m3u8_playlist, m3u8_playlist_url, quality):
    urls = _get_m3u8_urls_sorted(m3u8_playlist.text)
    stream_url = _select_stream_by_quality(urls, quality)
    if _is_stream_relative(stream_url):
        url = m3u8_playlist_url.split('?')[0]
        stream_url = urljoin(url, stream_url)
    return stream_url


# Return tuple: (bandwidth, resolution, avg_bandwidth, url)
M3U8_PATTERN = re.compile('#EXT-X-STREAM-INF:(?:BANDWIDTH=(?P<bandwidth>\d+),?|RESOLUTION=\d+x(?P<resolution>\d+),?|AVERAGE-BANDWIDTH=(?P<avg_bandwidth>\d+),?|[a-zA-Z_-]+=.*?,?)*\n(?P<url>.*)')
def _get_m3u8_urls_sorted(m3u8_playlist):
    urls = re.findall(M3U8_PATTERN, m3u8_playlist)
    urls = sorted(urls, key=lambda x: (x[1], x[2], x[0], -len(x[3])))
    return [x[3] for x in urls]


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
