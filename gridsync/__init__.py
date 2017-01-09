"""Synchronize local directories with Tahoe-LAFS storage grids."""

import os
import sys

from gridsync import _version


__author__ = 'Christopher R. Wood'
__url__ = 'https://github.com/gridsync/gridsync'
__license__ = 'GPL'
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


if sys.platform == 'win32':
    config_dir = os.path.join(os.getenv('APPDATA'), 'Gridsync')
elif sys.platform == 'darwin':
    config_dir = os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support', 'Gridsync')
else:
    config_home = os.environ.get(
        'XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    config_dir = os.path.join(config_home, 'gridsync')
