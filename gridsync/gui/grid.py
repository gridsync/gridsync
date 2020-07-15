# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtCore import QItemSelectionModel, QFileInfo, QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QFileIconProvider,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QShortcut,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QToolButton,
    QWidget,
)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir, settings
from gridsync.gui.color import BlendedColor
from gridsync.gui.files_view import FilesView
from gridsync.gui.font import Font
from gridsync.gui.history import HistoryView
from gridsync.gui.pixmap import CompositePixmap
from gridsync.gui.share import InviteReceiverDialog, InviteSenderDialog
from gridsync.gui.status import StatusPanel

# from gridsync.gui.view import View
from gridsync.gui.welcome import WelcomeDialog
from gridsync.msg import error, info
from gridsync.recovery import RecoveryKeyExporter
from gridsync.util import strip_html_tags


class NavigationBar(QWidget):
    def __init__(self, gui, gateway):
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        layout = QGridLayout(self)

        self.pb = QPushButton(self.gateway.name)

        self.lineedit = QLineEdit(self)
        self.lineedit.setStyleSheet(
            "QLineEdit { border: 2px grey; border-radius: 10px; padding: 5px }"
        )

        layout.addWidget(self.pb, 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 0, 2)
        layout.addWidget(self.lineedit, 1, 3)


class GridWidget(QWidget):
    def __init__(self, gui, gateway):
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        self.views = []
        self.folders_views = {}
        self.history_views = {}

        layout = QGridLayout(self)
        left, _, right, _ = layout.getContentsMargins()
        layout.setContentsMargins(0, 0, 0, 0)

        nav_bar = NavigationBar(self.gui, self.gateway)

        self.folders_view = FilesView(self.gui, self.gateway)

        history_view = HistoryView(gateway, self.gui)
        history_view.setMaximumWidth(500)  # XXX
        history_view.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        status_panel = StatusPanel(gateway, self.gui)

        layout.addWidget(nav_bar, 1, 1, 1, 2)
        layout.addWidget(self.folders_view, 2, 1)
        layout.addWidget(history_view, 2, 2)
        layout.addWidget(status_panel, 3, 1, 1, 2)

        nav_bar.lineedit.textChanged.connect(self.folders_view.update_location)
        nav_bar.pb.clicked.connect(
            lambda: self.folders_view.update_location(self.gateway.name)
        )

    def add_folders_view(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform == "darwin":
            # XXX: For some reason, getContentsMargins returns 20 px on macOS..
            layout.setContentsMargins(11, 11, 11, 0)
        else:
            left, _, right, _ = layout.getContentsMargins()
            layout.setContentsMargins(left, 0, right, 0)
        layout.addWidget(view)
        layout.addWidget(StatusPanel(gateway, self.gui))
        self.addWidget(widget)
        self.views.append(view)
        self.folders_views[gateway] = widget

    def add_history_view(self, gateway):
        view = HistoryView(gateway, self.gui)
        self.addWidget(view)
        self.history_views[gateway] = view

