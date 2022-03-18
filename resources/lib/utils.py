# coding=utf-8
import os
from os import path
import platform
import shutil
import requests
import zipfile
from . import tipsport_exceptions as Exceptions
from xbmc import log as log_fce

GITHUB_CODE_URL = 'https://github.com/JKubovy/plugin.video.tipsport.elh/'


def log(message):
    log_fce('|plugin.video.tipsport.elh|\t{0}'.format(message))


def get_host_info():
    try:
        return {
            'Host': {
                'System': platform.system(),
                'Node': platform.node(),
                'Release': platform.release(),
                'Version': platform.version(),
                'Machine': platform.machine(),
                'Processor': platform.processor()
            },
            'Python': {
                'Implementation': platform.python_implementation(),
                'Version': platform.python_version(),
                'Compiler': platform.python_compiler()
            }
        }
    except Exception:
        return None


def update_code_from_git(kodi_helper):
    try:
        tmp_file = path.join(kodi_helper.tmp_path, 'new_version.zip')
        download_file(GITHUB_CODE_URL + 'archive/refs/heads/master.zip', tmp_file)
        with zipfile.ZipFile(tmp_file, 'r') as zip_ref:
            code_folder = zip_ref.filelist[0].filename
            for archive_item in zip_ref.filelist:
                if archive_item.filename.startswith(code_folder):
                    destpath = path.join(kodi_helper.plugin_path, archive_item.filename[len(code_folder):])
                    os.makedirs(path.dirname(destpath), exist_ok=True)
                    if archive_item.is_dir():
                        continue
                    with zip_ref.open(archive_item) as source:
                        with open(destpath, 'wb') as dest:
                            shutil.copyfileobj(source, dest)
        os.remove(tmp_file)
    except Exception as ex:
        log(str(ex))
        raise Exceptions.UnableToUpdateCodeFromGit()


def download_file(url, path):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(path, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
