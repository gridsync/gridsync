# -*- coding: utf-8 -*-


from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap

from gridsync import resource


class Pixmap(QPixmap):
    def __init__(self, resource_filename, size=None):
        super().__init__(resource(resource_filename))
        if size:
            self.swap(self.scaled(
                size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))


class CompositePixmap(QPixmap):
    def __init__(self, pixmap, overlay=None, grayout=False):
        super(CompositePixmap, self).__init__()
        base_pixmap = QPixmap(pixmap)
        if grayout:
            painter = QPainter(base_pixmap)
            painter.setCompositionMode(painter.CompositionMode_SourceIn)
            painter.fillRect(base_pixmap.rect(), QColor(128, 128, 128, 128))
            painter.end()
        if overlay:
            width = int(base_pixmap.size().width() / 2)
            height = int(base_pixmap.size().height() / 2)
            overlay_pixmap = QPixmap(overlay).scaled(width, height)
            painter = QPainter(base_pixmap)
            painter.drawPixmap(width, height, overlay_pixmap)
            painter.end()
        self.swap(base_pixmap)
