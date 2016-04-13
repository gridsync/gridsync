# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import pprint


pprint.pprint(dict(os.environ))

try:
    from PyQt5 import QtCore
    print("QT_VERSION_STR: ", QtCore.QT_VERSION_STR)
    print("PYQT_VERSION_STR: ", QtCore.PYQT_VERSION_STR)
except ImportError as err:
    print(err)
    # TODO: create fixture to skip Qt tests
