# -*- coding: utf-8 -*-

import os

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from gridsync import resource
from gridsync.gui.files_view import FilesView
from gridsync.gui.history import HistoryView
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.status import StatusPanel


class LocationButton(QPushButton):
    def __init__(self, location, folders_view):
        super().__init__(os.path.basename(location))
        self.setFlat(True)
        self.setStyleSheet("font: 16px")
        self.setMaximumWidth(
            self.fontMetrics().boundingRect(self.text()).width() * 1.5  # XXX
        )
        self.clicked.connect(lambda: folders_view.update_location(location))


class LocationBox(QWidget):
    def __init__(self, folders_view):
        super().__init__()
        self.folders_view = folders_view

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.on_location_updated(self.folders_view.gateway.name)

    @Slot(str)
    def on_location_updated(self, location: str) -> None:
        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().deleteLater()
        directories = location.split(os.path.sep)
        len_directories = len(directories)
        for i, _ in enumerate(directories, start=1):
            self.layout.addWidget(
                LocationButton(
                    os.path.sep.join(directories[:i]), self.folders_view
                )
            )
            if i < len_directories:
                chevron = QLabel()
                chevron.setPixmap(Pixmap(resource("chevron-right.png"), 10))
                self.layout.addWidget(chevron)
        # self.layout.addWidget(QLabel("v"))
        # self.layout.addWidget(l)


class SearchBox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setPlaceholderText("Search")
        self.setStyleSheet(
            "QLineEdit { border-radius: 15px; padding: 6px; font: 14px }"
        )
        self.addAction(
            QAction(QIcon(resource("search.png")), "Search", self), 0
        )


class NavigationPanel(QWidget):
    def __init__(self, gui, gateway, folders_view):
        super().__init__()
        self.gui = gui
        self.gateway = gateway
        self.folders_view = folders_view

        self.layout = QGridLayout(self)

        self.nav_button = LocationBox(folders_view)
        self.lineedit = SearchBox(self)

        self.layout.addWidget(self.nav_button, 1, 1)
        self.layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 0, 2)
        self.layout.addWidget(self.lineedit, 1, 3)


class GridWidget(QWidget):
    def __init__(self, gui, gateway):
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        self.views = []
        self.folders_views = {}
        self.history_views = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.folders_view = FilesView(self.gui, self.gateway)

        nav_bar = NavigationPanel(self.gui, self.gateway, self.folders_view)

        history_view = HistoryView(
            gateway, deduplicate=False, max_items=100000
        )
        history_view.setMaximumWidth(550)  # XXX
        history_view.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        status_panel = StatusPanel(gateway, self.gui)

        layout.addWidget(nav_bar, 1, 1, 1, 2)
        layout.addWidget(self.folders_view, 2, 1)
        layout.addWidget(history_view, 2, 2)
        layout.addWidget(status_panel, 3, 1, 1, 2)

        nav_bar.lineedit.textChanged.connect(self.folders_view.update_location)
        # nav_bar.pb.clicked.connect(
        #    lambda: self.folders_view.update_location(self.gateway.name)
        # )
        self.folders_view.location_updated.connect(
            nav_bar.nav_button.on_location_updated
        )
