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
try:
    shutil.copytree(os.path.join('dist', name), appdir_bin)
except OSError:
    pass


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
os.environ['APPIMAGE_EXTRACT_AND_RUN'] = '1'
linuxdeploy_args = [
    'linuxdeploy',
    '--appdir=build/AppDir',
    '--executable={}'.format(os.path.join(appdir_usr, 'bin', name_lower)),
    '--icon-file={}'.format(icon_filepath),
    '--desktop-file={}'.format(desktop_filepath),
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


for file in sorted(os.listdir(appdir_bin)):
    # The `linuxdeploy` utility adds a copy of each library to AppDir/usr/lib,
    # however, the main PyInstaller-generated ("gridsync") executable expects
    # these libraries to be located in the same directory as the ("gridsync")
    # executable itself (resulting in *two* copies of each library and thus
    # wasted disk-space); removing the copies inserted by `linuxdeploy` -- and
    # and replacing them with symlinks to the originals -- saves disk-space.
    dst = 'build/AppDir/usr/lib/{}'.format(file)
    if os.path.exists(dst):
        try:
            os.remove(dst)
        except OSError:
            print('WARNING: Could not remove file {}'.format(dst))
            continue
        src = '../bin/{}'.format(file)
        print('Creating symlink: {} -> {}'.format(dst, src))
        try:
            os.symlink(src, dst)
        except OSError:
            print('WARNING: Could not create symlink for {}'.format(dst))


os.remove('build/AppDir/AppRun')
with open('build/AppDir/AppRun', 'w') as f:
    f.write('''#!/bin/sh
exec "$(dirname "$(readlink -e "$0")")/usr/bin/{}" "$@"
'''.format(name_lower)
    )
os.chmod('build/AppDir/AppRun', 0o755)


# Some distros (ubuntu-20.04, debian-10) have a default umask of 022
# while others (ubuntu-20.10, fedora-32) use 0002. Normalizing this
# helps to make the AppImage build deterministically/reproducibly.
for root, directories, files in os.walk("build/AppDir/usr/bin/resources"):
    for file in files:
        os.chmod(os.path.join(root, file), 0o644)
    for directory in directories:
        os.chmod(os.path.join(root, directory), 0o755)


# Created the .DirIcon symlink here/now to prevent appimagetool from
# doing it later, thereby allowing the atime and mtime of the symlink
# to be overriden along with all of the other files in the AppDir.
try:
    os.symlink(os.path.basename(icon_filepath), "build/AppDir/.DirIcon")
except OSError:
    pass

subprocess.call(["python3", "scripts/update_timestamps.py", "build/AppDir"])


try:
    os.mkdir('dist')
except OSError:
    pass
try:
    subprocess.call([
        'appimagetool', 'build/AppDir', 'dist/{}.AppImage'.format(name)
    ])
except OSError:
    sys.exit(
        'ERROR: `appimagetool` utility not found. Please ensure that it is '
        'on your $PATH and executable as `appimagetool` and try again.\n'
        '`appimagetool` can be downloaded from https://github.com/AppImage/A'
        'ppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage'
    )
