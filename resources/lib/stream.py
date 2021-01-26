from .utils import log


class RTMPStream:
    """Class represent one stream and store metadata used to generate rtmp stream link"""
    def __init__(self, rtmp_url, playpath, app, live_stream):
        self._rtmp_url = rtmp_url
        self._playpath = playpath
        self._app = app
        self._live_stream = live_stream

    def get_link(self):
        result = '{rtmp_url} playpath={playpath} app={app}{live}'.format(rtmp_url=self._rtmp_url,
                                                                         playpath=self._playpath,
                                                                         app=self._app,
                                                                         live=' live=true' if self._live_stream else '')
        log('RTMPStream link: ' + result)
        return result

    def is_rtmp(self):
        return True


class PlainStream:
    """Class represent one stream and store metadata used to generate plain/hls stream link"""
    def __init__(self, url):
        self._url = url.strip()

    def get_link(self):
        log('PlainStream link: ' + self._url)
        return self._url

    def is_rtmp(self):
        return False
