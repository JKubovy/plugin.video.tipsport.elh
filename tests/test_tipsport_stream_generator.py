import unittest
import sys
import os
sys.path.append(os.path.join(sys.path[0], '..', 'resources', 'lib'))
import tipsport_stream_generator as tpg


class TestTipsportStreamGenerator(unittest.TestCase):
    def test_get_matches_both_menu_response(self):
        client = tpg.Tipsport('none', 'none')
        response = client.get_matches_both_menu_response()
        content = response.content.decode('unicode-escape')
        self.assertFalse('_remoteHandleException' in content)
        self.assertFalse('_remoteHandleBatchException' in content)
        self.assertFalse('<!DOCTYPE html>' in content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
