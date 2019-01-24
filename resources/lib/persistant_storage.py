# coding=utf-8
from os import path
try:
    import cPickle as pickle
except ImportError:
    import pickle
import time
import xbmc
import xbmcvfs

class PersistantStorage():
    def __init__(self, id):
        self._id = id
        self._path = xbmc.translatePath('special://temp//{0}'.format('plugin.video.tipsport.elh'))
        if not xbmcvfs.exists(self._path):
            xbmcvfs.mkdirs(self._path)
        self._backup_file = path.join(self._path, '{0}.data'.format(str(self._id)))
        self._lock = path.join(self._path, '{0}.lock'.format(str(self._id)))
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.save()

    def __contains__(self, key):
        return key in self._data

    def _is_locked(self):
        return xbmcvfs.exists(self._lock)

    def _lock_file(self):
        f = xbmcvfs.File(self._lock, 'wb')
        f.close()

    def _unlock_file(self):
        if self._is_locked():
            xbmcvfs.delete(self._lock)

    def _wait(self):
        for i in range(0,5):
            if self._is_locked():
                time.sleep(1)
                continue
            else:
                return True
        return False

    def load(self):
        try:
            if xbmcvfs.exists(self._backup_file):
                if self._wait():
                    self._lock_file()
                    f = xbmcvfs.File(self._backup_file, 'rb')
                    self._data = pickle.loads(f.read())
                    f.close()
                    self._unlock_file()
                    return True
                else:
                    return False
            else:
                return False
        except:
            return False
        finally:
            self._unlock_file()

    def save(self):
        try:
            if self._wait():
                f = xbmcvfs.File(self._backup_file, 'wb')
                pickle.dump(self._data, f)
                f.close()
            else:
                f = xbmcvfs.File(self._backup_file, 'wb')
                pickle.dump(self._data, f)
                f.close()
                self._unlock_file()
        except:
            pass
        finally:
            self._unlock_file()