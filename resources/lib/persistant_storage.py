# coding=utf-8
from os import path
try:
    import cPickle as pickle
except ImportError:
    import pickle
import xbmc
import xbmcvfs

class PersistantStorage():
    def __init__(self, id):
        self._id = id
        self._path = xbmc.translatePath('special://temp//{0}'.format('plugin.video.tipsport.elh'))
        if not xbmcvfs.exists(self._path):
            xbmcvfs.mkdirs(self._path)
        self._backup_file = path.join(self._path, '{0}.data'.format(str(self._id)))
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.save()

    def __contains__(self, key):
        return key in self._data

    def load(self):
        if xbmcvfs.exists(self._backup_file):
            f = xbmcvfs.File(self._backup_file, 'rb')
            self._data = pickle.loads(f.read())
            f.close()
            return True
        else:
            return False

    def save(self):
        f = xbmcvfs.File(self._backup_file, 'wb')
        pickle.dump(self._data, f)
        f.close()
