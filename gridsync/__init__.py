"""Synchronize local directories with Tahoe-LAFS storage grids."""

import sys

from gridsync import _version


__author__ = 'Christopher R. Wood'
__url__ = 'https://github.com/gridsync/gridsync'
__license__ = 'GPL'
__version__ = _version.__version__


if getattr(sys, 'frozen', False):
    try:
        del sys.modules['twisted.internet.reactor']  # PyInstaller workaround
    except KeyError:
        pass
