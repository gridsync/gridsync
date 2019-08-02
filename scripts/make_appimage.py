#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import glob
import hashlib
import os
import shutil
import subprocess
import sys
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


LINUXDEPLOY_URL = 'https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage'
LINUXDEPLOY_HASH = '3513c4b8ef190f6cf0c2d2665ada478e4c71ca1266f9bc8c2adfe2f0b13a0fbc'


appdir_usr = os.path.join('build', 'AppDir', 'usr')
appdir_bin = os.path.join(appdir_usr, 'bin')
try:
    os.makedirs(appdir_usr)
except OSError:
    pass


linuxdeploy_path = os.path.join('build', 'linuxdeploy-x86_64.AppImage')
urlretrieve(LINUXDEPLOY_URL, linuxdeploy_path)


hasher = hashlib.sha256()
with open(linuxdeploy_path, 'rb') as f:
    for block in iter(lambda: f.read(4096), b''):
        hasher.update(block)
sha256sum = hasher.hexdigest()
if sha256sum != LINUXDEPLOY_HASH:
    sys.exit(
        "Checksum of {} failed!\n"
        "Expected: {}\n"
        "Received: {}".format(linuxdeploy_path, LINUXDEPLOY_HASH, sha256sum)
    )


os.chmod(linuxdeploy_path, 0o755)


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join('gridsync', 'resources', 'config.txt'))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

name = settings['application']['name']
name_lower = name.lower()
linux_icon = settings['build']['linux_icon']


shutil.copytree(os.path.join('dist', name), appdir_bin)


_, ext = os.path.splitext(linux_icon)
icon_filepath = os.path.abspath(os.path.join('build', name_lower + ext))
shutil.copy2(linux_icon, icon_filepath)


desktop_filepath = os.path.join('build', '{}.desktop'.format(name))
with open(desktop_filepath, 'w') as f:
    f.write('''[Desktop Entry]
Categories=Utility;
Type=Application
Name={0}
Exec={1}
Icon={1}
'''.format(name, name_lower)
    )


os.environ['LD_LIBRARY_PATH'] = appdir_bin
os.environ['VERSION'] = 'Linux'
linuxdeploy_args = [
    linuxdeploy_path,
    '--appdir=build/AppDir',
    '--executable={}'.format(os.path.join(appdir_usr, 'bin', name_lower)),
    '--icon-file={}'.format(icon_filepath),
    '--desktop-file={}'.format(desktop_filepath),
    '--output=appimage'
]
returncode = subprocess.call(linuxdeploy_args)
if returncode:
    # XXX Ugly hack/workaround for "ERROR: Strip call failed: /tmp/.mount_linuxdns8a8k/usr/bin/strip: unable to copy file 'build/AppDir/usr/lib/libpython3.7m.so.1.0'; reason: Permission denied" observed on Travis-CI
    os.chmod(glob.glob('build/AppDir/usr/lib/libpython*.so.*')[0], 0o755)
    subprocess.call(linuxdeploy_args)


try:
    os.mkdir('dist')
except OSError:
    pass
shutil.move(
    '{}-Linux-x86_64.AppImage'.format(name),
    os.path.join('dist', '{}.AppImage'.format(name))
)
