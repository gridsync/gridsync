"""Synchronize local directories with Tahoe-LAFS storage grids."""

import os
import sys

from gridsync import _version


__author__ = 'Christopher R. Wood'
__url__ = 'https://github.com/gridsync/gridsync'
__license__ = 'GPL'
__version__ = _version.__version__


# Workarounds for PyInstaller
if getattr(sys, 'frozen', False):
    del sys.modules['twisted.internet.reactor']
    tahoe_bundle = os.path.join(os.path.dirname(sys.executable), 'Tahoe-LAFS')
    os.environ["PATH"] += os.pathsep + tahoe_bundle
