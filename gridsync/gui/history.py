# -*- coding: utf-8 -*-

from datetime import datetime
import os
import sys
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import QFileInfo, QTimer, Qt
from PyQt5.QtGui import QColor, QCursor, QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction, QAbstractItemView, QFileIconProvider, QGridLayout, QLabel,
    QListWidgetItem, QListWidget, QMenu, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)

from gridsync import resource
from gridsync.desktop import open_enclosing_folder, open_path
from gridsync.gui.status import StatusPanel


class HistoryItemWidget(QWidget):
    def __init__(self, gateway, folder_name, data, parent):
        super(HistoryItemWidget, self).__init__()
        self.gateway = gateway
        self.data = data
        self.parent = parent

        self.path = data['path']
        self.size = data['size']
        self.action = data['action']
        self.mtime = data['mtime']
        self._thumbnail_loaded = False

        self.setAutoFillBackground(True)

        directory = self.gateway.get_magic_folder_directory(folder_name)
        if directory:
            self.path = os.path.join(directory, self.path)
        self.basename = os.path.basename(os.path.normpath(self.path))

        self.setToolTip(
            "{}\n\nSize: {}\nModified: {}".format(
                self.path, naturalsize(self.size), time.ctime(self.mtime)
            )
        )

        self.icon = QLabel()
        self.icon.setPixmap(
            QFileIconProvider().icon(QFileInfo(self.path)).pixmap(48, 48)
        )

        self.basename_label = QLabel(self.basename)
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(15)
        else:
            font.setPointSize(11)
        self.basename_label.setFont(font)

        self.details_label = QLabel()
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(13)
        else:
            font.setPointSize(10)
        self.details_label.setFont(font)
        self.details_label.setStyleSheet('color: grey')

        self.button = QPushButton()
        self.button.setIcon(QIcon(resource('dots-horizontal-triple.png')))
        self.button.setStyleSheet('border: none;')
        self.button.clicked.connect(self.parent.on_right_click)
        self.button.hide()

        self.layout = QGridLayout(self)
        self.layout.addWidget(self.icon, 1, 1, 2, 2)
        self.layout.addWidget(self.basename_label, 1, 3)
        self.layout.addWidget(self.details_label, 2, 3)
        self.layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 4, 4)
        self.layout.addWidget(self.button, 1, 5, 2, 2)

        self.update_text()
        QTimer.singleShot(50, self.load_thumbnail)

    def update_text(self):
        self.details_label.setText(
            "{} {}".format(
                self.action.capitalize(),
                naturaltime(datetime.fromtimestamp(self.mtime)),
            )
        )

    def _do_load_thumbnail(self):
        pixmap = QPixmap(self.path)
        if not pixmap.isNull():
            self.icon.setPixmap(pixmap.scaled(48, 48))

    def load_thumbnail(self):
        if self.isVisible() and not self._thumbnail_loaded:
            self._thumbnail_loaded = True
            QTimer.singleShot(50, self._do_load_thumbnail)

    def unhighlight(self):
        self.button.hide()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.parent.base_color)
        self.setPalette(palette)

    def enterEvent(self, _):
        self.button.show()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.parent.highlighted_color)
        self.setPalette(palette)
        if self.parent.highlighted and self.parent.highlighted is not self:
            try:
                self.parent.highlighted.unhighlight()
            except RuntimeError:  # Object has been deleted
                pass
        self.parent.highlighted = self


class HistoryListWidget(QListWidget):
    def __init__(self, gateway, deduplicate=True, max_items=30):
        super(HistoryListWidget, self).__init__()
        self.gateway = gateway
        self.deduplicate = deduplicate
        self.max_items = max_items

        self.base_color = self.palette().base().color()
        self.highlighted_color = QColor("#E6F1F7")  # TODO: Get from theme?
        self.highlighted = None

        self.action_icon = QIcon(resource('dots-horizontal-triple.png'))

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        #self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        #self.setStyleSheet("QListWidget::item:hover { background: #E6F1F7 }")
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.sb = self.verticalScrollBar()

        self.sb.valueChanged.connect(self.update_visible_widgets)
        self.itemDoubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.gateway.monitor.file_updated.connect(self.add_item)
        self.gateway.monitor.check_finished.connect(
            self.update_visible_widgets
        )

    def on_double_click(self, item):
        open_enclosing_folder(self.itemWidget(item).path)

    def on_right_click(self, position):
        if not position:
            position = self.viewport().mapFromGlobal(QCursor().pos())
        item = self.itemAt(position)
        if not item:
            return
        widget = self.itemWidget(item)
        menu = QMenu(self)
        open_file_action = QAction("Open file")
        open_file_action.triggered.connect(lambda: open_path(widget.path))
        menu.addAction(open_file_action)
        open_folder_action = QAction("Open enclosing folder")
        open_folder_action.triggered.connect(
            lambda: self.on_double_click(item))
        menu.addAction(open_folder_action)
        menu.exec_(self.viewport().mapToGlobal(position))

    def add_item(self, folder_name, data):
        duplicate = None
        if self.deduplicate:
            for i in range(self.count()):
                widget = self.itemWidget(self.item(i))
                if widget and widget.data['path'] == data['path'] and \
                        widget.data['member'] == data['member']:
                    duplicate = i
                    break
        if duplicate is not None:
            item = self.takeItem(duplicate)
        else:
            self.takeItem(self.max_items)
            item = QListWidgetItem()
        self.insertItem(0 - int(data['mtime']), item)  # Newest on top
        custom_widget = HistoryItemWidget(
            self.gateway, folder_name, data, self)
        item.setSizeHint(custom_widget.sizeHint())
        self.setItemWidget(item, custom_widget)

    def update_visible_widgets(self):
        if not self.isVisible():
            return
        rect = self.viewport().contentsRect()
        top = self.indexAt(rect.topLeft())
        if top.isValid():
            bottom = self.indexAt(rect.bottomLeft())
            if not bottom.isValid():
                bottom = self.model().index(self.count() - 1)
            for index in range(top.row(), bottom.row() + 1):
                widget = self.itemWidget(self.item(index))
                if widget:
                    widget.update_text()
                    widget.load_thumbnail()

    def showEvent(self, _):
        self.update_visible_widgets()


class HistoryView(QWidget):
    def __init__(self, gateway, deduplicate=True, max_items=30):
        super(HistoryView, self).__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(HistoryListWidget(gateway, deduplicate, max_items))
        layout.addWidget(StatusPanel(gateway))
