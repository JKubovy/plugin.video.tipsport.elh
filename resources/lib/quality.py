from .tipsport_exceptions import UnknownException


class Quality(object):
    @staticmethod
    def parse(str_quality):
        if str_quality == '0':
            return Quality.LOW
        elif str_quality == '1':
            return Quality.MID
        elif str_quality == '2':
            return Quality.HIGH
        else:
            raise UnknownException('Unknown quality')

    LOW = 0
    MID = 1
    HIGH = 2
