# -*- coding: utf-8 -*-
"""Desktop integration functions"""

import os
import sys
import ConfigParser


def integrate():
    if sys.platform == 'linux2':
        _integrate_linux()

def _add_desktop_file():
    path = os.path.expanduser("~/.local/share/applications/gridsync.desktop")
    contents = """[Desktop Entry]
Name=Gridsync
Comment=Synchronize local directories with Tahoe-LAFS storage grids
Exec=gridsync %u
Icon=gridsync
Type=Application
MimeType=x-scheme-handler/gridsync
Terminal=false"""
    with open(path, 'w') as f:
        f.write(contents)

def _add_associations():
    config = ConfigParser.RawConfigParser()
    mimeapps_list = os.path.expanduser("~/.local/share/applications/mimeapps.list")
    config.read(mimeapps_list)
    if not config.has_section('Default Applications'):
        config.add_section('Default Applications')
    if not config.has_section('Added Associations'):
        config.add_section('Added Associations')
    config.set('Default Applications', 'x-scheme-handler/gridsync', 'gridsync.desktop')
    config.set('Added Associations', 'x-scheme-handler/gridsync', 'gridsync.desktop')
    with open(mimeapps_list, 'wb') as f:
        config.write(f)

def _integrate_linux():
    _add_desktop_file()
    _add_associations()


def deintegrate():
    if sys.platform == 'linux2':
        _deintegrate_linux()

def _remove_desktop_file():
    try:
        os.remove(os.path.expanduser("~/.local/share/applications/gridsync.desktop"))
    except:
        pass

def _remove_associations():
    config = ConfigParser.RawConfigParser()
    mimeapps_list = os.path.expanduser("~/.local/share/applications/mimeapps.list")
    config.read(mimeapps_list)
    config.remove_option('Default Applications', 'x-scheme-handler/gridsync')
    config.remove_option('Added Associations', 'x-scheme-handler/gridsync')
    with open(mimeapps_list, 'wb') as f:
        config.write(f)


def _deintegrate_linux():
    _remove_associations()
    _remove_desktop_file()

