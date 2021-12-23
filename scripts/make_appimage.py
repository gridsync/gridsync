#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import glob
import os
from pathlib import Path
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


appdir = Path("build", "AppDir")
try:
    appdir.mkdir(parents=True)
except OSError:
    pass
try:
    shutil.copytree(Path('dist', name), appdir.joinpath(name))
except OSError:
    raise


_, ext = os.path.splitext(linux_icon)
icon_path = appdir.joinpath("usr/share/icons/hicolor/scalable/apps")
icon_path.mkdir(parents=True)
icon_filepath = icon_path.joinpath(name_lower + ext)
shutil.copy2(linux_icon, appdir.joinpath(name_lower + ext))
icon_filepath.symlink_to(Path("../../../../../..", name_lower + ext))
 
desktop_filepath = appdir.joinpath('{}.desktop'.format(name))
desktop_filepath.write_text(
    '''[Desktop Entry]
Categories=Utility;
Type=Application
Name={0}
Exec={1}
Icon={1}
'''.format(name, name_lower)
)

appdir.joinpath("AppRun").symlink_to(Path(name).joinpath(name_lower))

os.environ['APPIMAGE_EXTRACT_AND_RUN'] = '1'


subprocess.run(["python3", "scripts/update_permissions.py", "build/AppDir"], check=True)
subprocess.run(["python3", "scripts/update_timestamps.py", "build/AppDir"], check=True)


try:
    os.mkdir('dist')
except OSError:
    pass
try:
    subprocess.run([
        'appimagetool', 'build/AppDir', 'dist/{}.AppImage'.format(name)
    ], check=True)
except OSError:
    sys.exit(
        'ERROR: `appimagetool` utility not found. Please ensure that it is '
        'on your $PATH and executable as `appimagetool` and try again.\n'
        '`appimagetool` can be downloaded from https://github.com/AppImage/A'
        'ppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage'
    )
