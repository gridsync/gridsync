# -*- coding: utf-8 -*-


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from gridsync import resource


class Pixmap(QPixmap):
    def __init__(self, resource_filename, size=None):
        super().__init__(resource(resource_filename))
        if size:
            self.swap(self.scaled(
                size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation 
            ))
