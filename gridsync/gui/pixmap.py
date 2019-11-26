# -*- coding: utf-8 -*-

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPixmap

from gridsync import resource


class Pixmap(QPixmap):
    def __init__(self, resource_filename, size=None):
        super().__init__(resource(resource_filename))
        if size:
            self.swap(
                self.scaled(
                    size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )


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


class BadgedPixmap(QPixmap):

    TopLeft = (0, 0)
    TopRight = (1, 0)
    BottomLeft = (0, 1)
    BottomRight = (1, 1)

    def __init__(self, pixmap, text, size=0.5, corner=BottomRight):
        super().__init__()

        base_pixmap = QPixmap(pixmap)
        base_size = base_pixmap.size()
        base_max = min(base_size.height(), base_size.width())
        if not base_max:
            # Because gridsync.gui.systray.animation.currentPixmap() returns
            # a blank pixmap when unpausing the animation for the first time.
            # Returning early to prevents QPainter from spewing warnings.
            self.swap(base_pixmap)
            return

        badge_max = base_max * size
        pen_width = badge_max * 0.05
        rect = QRect(
            base_max * max(corner[0] - size, 0) + pen_width,
            base_max * max(corner[1] - size, 0) + pen_width,
            badge_max - pen_width,
            badge_max - pen_width,
        )

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.red, pen_width))
        painter.setBrush(QBrush(Qt.red))
        painter.drawEllipse(rect)

        if text:
            font = painter.font()
            font.setPixelSize(badge_max - pen_width)
            painter.setFont(font)
            painter.setPen(Qt.white)
            painter.drawText(rect, Qt.AlignCenter, str(text))

        painter.end()
        self.swap(base_pixmap)
