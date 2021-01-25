class xbmc:
    def log(message):
        print(message, file=sys.stderr)
import sys
sys.modules['xbmc'] = xbmc
from resources.lib.tipsport_stream_generator import Tipsport
from resources.lib.user_data import UserData


def test_login(tipsport) -> bool:
    try:
        tipsport.login()
        return tipsport.is_logged_in()
    except:
        return False


def test_all_streams(tipsport) -> None:
    tipsport.login()
    matches = tipsport.get_list_elh_matches(None)
    for match in matches:
        try:
            if match.is_stream_enabled():
                tipsport.get_stream(match.url).get_link()
        except:
            pass


def _get_tipsport(username, password) -> Tipsport:
    return Tipsport(UserData(username, password, 'tipsport.cz'), None)


if __name__ == '__main__':
    tipsport = _get_tipsport(input('username: '), input('password: '))
    test_all_streams(tipsport)
