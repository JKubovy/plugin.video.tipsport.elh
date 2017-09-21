class TpgException(Exception):
    def __init__(self, message):
        super(TpgException, self).__init__(message)


class NoInternetConnectionsException(TpgException):
    def __init__(self, message='Check internet connection'):
        super(NoInternetConnectionsException, self).__init__(message)


class LoginFailedException(TpgException):
    def __init__(self, message='Login failed. Check username/password'):
        super(LoginFailedException, self).__init__(message)


class UnableGetStreamMetadataException(TpgException):
    def __init__(self, message='Unable to get stream metadata'):
        super(UnableGetStreamMetadataException, self).__init__(message)


class UnableParseStreamMetadataException(TpgException):
    def __init__(self, message='Unable to parse stream metadata'):
        super(UnableParseStreamMetadataException, self).__init__(message)


class UnsupportedFormatStreamMetadataException(TpgException):
    def __init__(self, message='Unsupported format of stream metadata'):
        super(UnsupportedFormatStreamMetadataException, self).__init__(message)


class UnableDetectScriptSessionIdException(TpgException):
    def __init__(self, message='Unable to detect scriptSessionId'):
        super(UnableDetectScriptSessionIdException, self).__init__(message)


class UnableGetStreamNumberException(TpgException):
    def __init__(self, message='Unable to get StreamNumber'):
        super(UnableGetStreamNumberException, self).__init__(message)


class StreamHasNotStarted(TpgException):
    def __init__(self, message='Stream has not been started yet'):
        super(StreamHasNotStarted, self).__init__(message)
