"""Synchronize local directories with Tahoe-LAFS storage grids."""

import os
import sys

# Workarounds for PyInstaller
if getattr(sys, 'frozen', False):
    del sys.modules['twisted.internet.reactor']
    tahoe_bundle = os.path.join(os.path.dirname(sys.executable), 'Tahoe-LAFS')
    os.environ["PATH"] += os.pathsep + tahoe_bundle

#from PyQt5.QtWidgets import QApplication
#app = QApplication(sys.argv)
#import qt5reactor
#qt5reactor.install()

from gridsync import _version

__author__ = 'Christopher R. Wood'
__url__ = 'https://github.com/gridsync/gridsync'
__license__ = 'GPL'
__version__ = _version.__version__
