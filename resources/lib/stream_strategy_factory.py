import json
from .utils import log
from .tipsport_exceptions import UnableGetStreamNumberException, TipsportMsg, StreamHasNotStarted, UnableGetStreamMetadataException
from . import stream_strategy as Strategies


class StreamStrategyFactory:
    def __init__(self, session, user_data):
        self._session = session
        self._user_data = user_data

    def get_stream_strategy(self, relative_url):
        stream_number = self._get_stream_number(relative_url)
        base_url = self._user_data.site_mobile + '/rest/offer/v2/live/matches/{stream_number}/stream?deviceType=DESKTOP'.format(
            stream_number=stream_number)
        if not self._has_stream_started(base_url):
            raise StreamHasNotStarted()
        stream_strategy = self._try_hls_strategy(base_url)
        if stream_strategy:
            return stream_strategy
        stream_strategy = self._try_rtmp_strategy(base_url)
        if stream_strategy:
            return stream_strategy
        stream_strategy = self._try_rtmp_with_hls_strategy(base_url)
        if stream_strategy:
            return stream_strategy
        return Strategies.NoneStrategy(relative_url)

        # stream_source, stream_type, url = self._get_stream_source_type_and_data(relative_url)
        # if stream_type == 'RTMP':
        #     return RTMPStreamStrategy(url)

        # if stream_source in ['LIVEBOX_ELH', 'LIVEBOX_SK']:
        #     if stream_type == 'RTMP':
        #         return self._decode_rtmp_url(url)
        #     elif stream_type == 'HLS':
        #         return self._get_hls_stream(url, True)
        #     else:
        #         raise UnableGetStreamMetadataException()
        # elif stream_source == 'MANUAL':
        #     stream_url = self.user_data.site + '/live' + relative_url
        #     page = self.session.get(stream_url)
        #     return self._get_hls_stream_from_page(page.text)
        # elif stream_source == 'HUSTE':
        #     return self._get_hls_stream(url)
        # else:
        #     raise UnableGetStreamMetadataException()

    def _try_rtmp_strategy(self, base_url_request):
        url_request = base_url_request + '&format=RTMP'
        response = self._session.get(url_request)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if stream_type == 'RTMP' and data is not None:
                return Strategies.RTMPStreamStrategy(data)
            log('Unknown RTMP stream_type: ' + stream_type + ', stream_source: ' + stream_source)
        except Exception:
            pass
        return None

    def _try_hls_strategy(self, base_url_request):
        url_request = base_url_request + '&format=HLS'
        response = self._session.get(url_request)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if stream_type == 'HLS':
                return Strategies.HLSStreamStrategy(self._session, data)
            if stream_type == 'URL_IMG':
                return Strategies.UrlImgStreamStrategy(self._session, data)
            if stream_type == 'URL_AGURA':
                return Strategies.UrlAguraStrategy(self._session, data)
            log('Unknown HLS stream_type: ' + stream_type + ', stream_source: ' + stream_source)
        except Exception:
            pass
        return None

    def _try_rtmp_with_hls_strategy(self, base_url_request):
        url_request = base_url_request + '&format=RTMP_WITH_HLS'
        response = self._session.get(url_request)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if stream_type == 'RTMP_WITH_HLS':
                url = data.split('###')[1]
                return Strategies.HLSStreamStrategy(self._session, url)
            log('Unknown RTMP_WITH_HLS stream_type: ' + stream_type + ', stream_source: ' + stream_source)
        except Exception:
            pass
        return None

    def _try_other_strategy(self, base_url_request):
        url_request = base_url_request + '&format=OTHER'
        response = self._session.get(url_request)
        try:
            stream_source, stream_type, data = self._parse_stream_info_response(response)
            if stream_type == 'URL_PERFORM':
                return Strategies.UrlPerformeStreamStrategy(self._session, data)
            if stream_type == 'URL_TVCOM':
                return Strategies.TvComStreamStrategy(self._session, data)
            log('Unknown OTHER stream_type: ' + stream_type + ', stream_source: ' + stream_source)
        except Exception:
            pass
        return None

    # def _get_stream_source_type_and_data(self, relative_url):
    #     """Get source and type of stream"""
    #     stream_number = self._get_stream_number(relative_url)
    #     base_url = self._user_data.site_mobile + '/rest/offer/v2/live/matches/{stream_number}/stream?deviceType=DESKTOP'.format(
    #         stream_number=stream_number)
    #     url = base_url + '&format=HLS'
    #     response = self._session.get(url)
    #     try:
    #         stream_source, stream_type, data = self._parse_stream_info_response(response)
    #         if 'auth=' not in data:
    #             url = base_url + '&format=RTMP'
    #             response = self._session.get(url)
    #             stream_source, stream_type, data = self._parse_stream_info_response(response)
    #         return stream_source, stream_type, data
    #     except (TypeError, KeyError):
    #         raise UnableGetStreamMetadataException()

    def _has_stream_started(self, base_url):
        response = self._session.get(base_url)
        _, stream_type, _ = self._parse_stream_info_response(response)
        return stream_type != 'INF'

    @staticmethod
    def _get_stream_number(relative_url):
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

    @staticmethod
    def _parse_stream_info_response(response):
        try:
            data = json.loads(response.text)
            if 'displayRules' not in data:
                raise UnableGetStreamMetadataException()
            if data['displayRules'] is None:
                raise (TipsportMsg(data['data']))
            stream_source = data['source']
            stream_type = data['type']
            return stream_source, stream_type, data['data']
        except ValueError:
            raise UnableGetStreamMetadataException()
