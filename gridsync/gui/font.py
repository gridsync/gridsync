# -*- coding: utf-8 -*-

import sys

from PyQt5.QtGui import QFont


class Font(QFont):
    def __init__(self, point_size=12):
        super().__init__()
        if sys.platform == "darwin":
            if point_size >= 11:
                self.setPointSize(point_size + 4)
            else:
                self.setPointSize(point_size + 3)
        else:
            self.setPointSize(point_size)
