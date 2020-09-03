from .tipsport_exceptions import UnknownException


class Site(object):
    @staticmethod
    def parse(str_site):
        if str_site == '0':
            return Site.CZ
        elif str_site == '1':
            return Site.SK
        else:
            raise UnknownException('Unknown site')

    CZ = 'tipsport.cz'
    SK = 'tipsport.sk'
