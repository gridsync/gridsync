"""Synchronize local directories with Tahoe-LAFS storage grids."""

import os
import sys

from gridsync import _version
from gridsync.config import Config

__author__ = 'Christopher R. Wood'
__url__ = 'https://github.com/gridsync/gridsync'
__license__ = 'GPLv3'
__version__ = _version.__version__


if getattr(sys, 'frozen', False):
    pkgdir = os.path.dirname(os.path.realpath(sys.executable))
    os.environ["PATH"] += os.pathsep + os.path.join(pkgdir, 'Tahoe-LAFS')
    try:
        del sys.modules['twisted.internet.reactor']  # PyInstaller workaround
    except KeyError:
        pass
else:
    pkgdir = os.path.dirname(os.path.realpath(__file__))


settings = Config(os.path.join(pkgdir, 'resources', 'config.txt')).load()

try:
    APP_NAME = settings['application']['name']
except KeyError:
    APP_NAME = 'Gridsync'

if sys.platform == 'win32':
    config_dir = os.path.join(
        os.getenv('APPDATA'), APP_NAME)
    autostart_file_path = os.path.join(
        os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs',
        'Startup', APP_NAME + '.lnk')
elif sys.platform == 'darwin':
    config_dir = os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support', APP_NAME)
    autostart_file_path = os.path.join(
        os.path.expanduser('~'), 'Library', 'LaunchAgents', APP_NAME + '.plist'
    )
else:
    config_home = os.environ.get(
        'XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    config_dir = os.path.join(
        config_home, APP_NAME.lower())
    autostart_file_path = os.path.join(
        config_home, 'autostart', APP_NAME + '.desktop')


def resource(filename):
    return os.path.join(pkgdir, 'resources', filename)
