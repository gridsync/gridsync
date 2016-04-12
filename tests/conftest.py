# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import pprint


pprint.pprint(dict(os.environ))

from PyQt5.QtWidgets import QApplication
app = QApplication([])
print(app)
