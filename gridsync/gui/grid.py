# -*- coding: utf-8 -*-

import logging
import os

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)
from twisted.internet.defer import DeferredList, inlineCallbacks

from gridsync import resource, APP_NAME
from gridsync.gui.files_view import FilesView
from gridsync.gui.history import HistoryListWidget
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.status import StatusPanel
from gridsync.msg import error


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

        self.search_box.textChanged.connect(files_view.update_search_filter)
        files_view.location_updated.connect(
            self.location_box.on_location_updated
        )


class GridWidget(QWidget):
    def __init__(self, gui, gateway):
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        self._restart_required = False

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
            history_list_widget.filter_by_location
        )
        self.files_view.selection_updated.connect(
            history_list_widget.filter_by_remote_paths
        )

    @inlineCallbacks
    def maybe_restart_gateway(self, _):
        if self._restart_required:
            self._restart_required = False
            logging.debug("A restart was scheduled; restarting...")
            yield self.gateway.restart()
        else:
            logging.debug("No restarts were scheduled; not restarting")

    @inlineCallbacks
    def add_folder(self, path):
        path = os.path.realpath(path)
        self.files_view.source_model.add_folder(path)  # XXX
        folder_name = os.path.basename(path)
        try:
            yield self.gateway.create_magic_folder(path)
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self,
                'Error adding folder "{}"'.format(folder_name),
                'An exception was raised when adding the "{}" folder:\n\n'
                "{}: {}\n\nPlease try again later.".format(
                    folder_name, type(e).__name__, str(e)
                ),
            )
            self.files_view.source_model.remove_folder(folder_name)  # XXX
            return
        self._restart_required = True
        logging.debug(
            'Successfully added folder "%s"; scheduled restart', folder_name
        )

    def add_folders(self, paths):
        paths_to_add = []
        for path in paths:
            basename = os.path.basename(os.path.normpath(path))
            if not os.path.isdir(path):
                error(
                    self,
                    'Cannot add "{}".'.format(basename),
                    "{} only supports uploading and syncing folders,"
                    " and not individual files.".format(APP_NAME),
                )
            elif self.gateway.magic_folder_exists(basename):
                error(
                    self,
                    "Folder already exists",
                    'You already belong to a folder named "{}" on {}. Please '
                    "rename it and try again.".format(
                        basename, self.gateway.name
                    ),
                )
            else:
                paths_to_add.append(path)
        if paths_to_add:
            tasks = []
            for path in paths_to_add:
                tasks.append(self.add_folder(path))
            d = DeferredList(tasks)
            d.addCallback(self.maybe_restart_gateway)

    def select_folder(self):
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser("~"))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            self.add_folders(dialog.selectedFiles())
