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
from gridsync.gui.history import HistoryListWidget
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.status import StatusPanel


class LocationButton(QPushButton):
    def __init__(self, location, files_view):
        super().__init__(os.path.basename(location))
        self.setFlat(True)
        self.setStyleSheet("font: 16px")
        self.setMaximumWidth(
            self.fontMetrics().boundingRect(self.text()).width() * 1.5  # XXX
        )
        self.clicked.connect(lambda: files_view.update_location(location))


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


class SearchBox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setPlaceholderText("Search")
        self.setStyleSheet(
            "QLineEdit { border-radius: 15px; padding: 6px; font: 14px }"
        )

        self.clear_action = QAction(
            QIcon(resource("close.png")), "Clear", self
        )

        self.addAction(
            QAction(QIcon(resource("search.png")), "Search", self), 0
        )
        self.addAction(self.clear_action, 1)

        self.textChanged.connect(self.on_text_changed)
        self.clear_action.triggered.connect(self.on_clear_action_triggered)

        self.on_text_changed("")

    @Slot(str)
    def on_text_changed(self, text: str) -> None:
        if text:
            self.clear_action.setEnabled(True)
            self.clear_action.setVisible(True)
        else:
            self.clear_action.setEnabled(False)
            self.clear_action.setVisible(False)

    def on_clear_action_triggered(self):
        self.setText("")


class NavigationPanel(QWidget):
    def __init__(self, gui, gateway, files_view):
        super().__init__()
        self.gui = gui
        self.gateway = gateway
        self.files_view = files_view

        layout = QGridLayout(self)

        self.location_box = LocationBox(files_view)
        self.search_box = SearchBox(self)

        layout.addWidget(self.location_box, 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 0, 2)
        layout.addWidget(self.search_box, 1, 3)

        self.search_box.textChanged.connect(files_view.update_location)
        files_view.location_updated.connect(
            self.location_box.on_location_updated
        )


class GridWidget(QWidget):
    def __init__(self, gui, gateway):
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.files_view = FilesView(self.gui, self.gateway)

        navigation_panel = NavigationPanel(
            self.gui, self.gateway, self.files_view
        )

        history_list_widget = HistoryListWidget(
            gateway, deduplicate=False, max_items=100000
        )
        history_list_widget.setMaximumWidth(550)
        history_list_widget.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Minimum
        )

        status_panel = StatusPanel(gateway, self.gui)

        layout.addWidget(navigation_panel, 1, 1, 1, 2)
        layout.addWidget(self.files_view, 2, 1)
        layout.addWidget(history_list_widget, 2, 2)
        layout.addWidget(status_panel, 3, 1, 1, 2)

        self.files_view.location_updated.connect(
            history_list_widget.on_location_updated
        )
