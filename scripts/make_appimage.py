#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import glob
import os
import shutil
import subprocess
import sys


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


appdir_usr = os.path.join('build', 'AppDir', 'usr')
appdir_bin = os.path.join(appdir_usr, 'bin')
try:
    os.makedirs(appdir_usr)
except OSError:
    pass
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
    'linuxdeploy',
    '--appdir=build/AppDir',
    '--executable={}'.format(os.path.join(appdir_usr, 'bin', name_lower)),
    '--icon-file={}'.format(icon_filepath),
    '--desktop-file={}'.format(desktop_filepath),
    '--output=appimage'
]
try:
    returncode = subprocess.call(linuxdeploy_args)
except OSError:
    sys.exit(
        'ERROR: `linuxdeploy` utility not found. Please ensure that it is '
        'on your $PATH and executable as `linuxdeploy` and try again.\n'
        '`linuxdeploy` can be downloaded from https://github.com/linuxdeploy/'
        'linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage'
    )
if returncode:
    # XXX Ugly hack/workaround for "ERROR: Strip call failed: /tmp/.mount_linuxdns8a8k/usr/bin/strip: unable to copy file 'build/AppDir/usr/lib/libpython3.7m.so.1.0'; reason: Permission denied" observed on Travis-CI
    os.chmod(glob.glob('build/AppDir/usr/lib/libpython*.so.*')[0], 0o755)
    subprocess.call(linuxdeploy_args)


def deduplicate_libs():
    appimage = os.path.abspath('{}-Linux-x86_64.AppImage'.format(name))
    size_before = os.path.getsize(appimage)
    subprocess.call([appimage, '--appimage-extract'])
    os.remove(appimage)
    shutil.rmtree('build/AppDir')
    shutil.move('squashfs-root', 'build/AppDir')
    for file in sorted(os.listdir('build/AppDir/usr/bin')):
        path = 'build/AppDir/usr/lib/{}'.format(file)
        if os.path.exists(path):
            print('Removing duplicate library:', path)
            try:
                os.remove(path)
            except OSError:
                print('WARNING: Could not remove file {}'.format(path))
    subprocess.call(['appimagetool', 'build/AppDir', appimage])
    size_after = os.path.getsize(appimage)
    print('Reduced filesize by {} bytes.'.format(size_before - size_after))

deduplicate_libs()


try:
    os.mkdir('dist')
except OSError:
    pass
shutil.move(
    '{}-Linux-x86_64.AppImage'.format(name),
    os.path.join('dist', '{}.AppImage'.format(name))
)
