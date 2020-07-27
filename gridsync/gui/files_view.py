# -*- coding: utf-8 -*-

import logging
import os

from PyQt5.QtCore import QPoint, QSize, QSortFilterProxyModel, Qt
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QHeaderView,
    QStyledItemDelegate,
    QTableView,
)
from twisted.internet.defer import DeferredList, inlineCallbacks

from gridsync import resource, APP_NAME
from gridsync.gui.font import Font
from gridsync.gui.files_model import FilesModel
from gridsync.monitor import MagicFolderChecker
from gridsync.msg import error


class Delegate(QStyledItemDelegate):
    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.waiting_movie = QMovie(resource("waiting.gif"))
        self.waiting_movie.setCacheMode(True)
        self.waiting_movie.frameChanged.connect(self.on_frame_changed)
        self.sync_movie = QMovie(resource("sync.gif"))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self):
        values = self.view.source_model.status_dict.values()
        if (
            MagicFolderChecker.LOADING in values
            or MagicFolderChecker.SYNCING in values
            or MagicFolderChecker.SCANNING in values
        ):
            self.view.viewport().update()
        else:
            self.waiting_movie.setPaused(True)
            self.sync_movie.setPaused(True)

    def paint(self, painter, option, index):
        column = index.column()
        # if column == 1:
        if column == self.view.source_model.STATUS_COLUMN:
            pixmap = None
            status = index.data(Qt.UserRole)
            if status == MagicFolderChecker.LOADING:
                self.waiting_movie.setPaused(False)
                pixmap = self.waiting_movie.currentPixmap().scaled(
                    32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            elif status in (
                MagicFolderChecker.SYNCING,
                MagicFolderChecker.SCANNING,
            ):
                self.sync_movie.setPaused(False)
                pixmap = self.sync_movie.currentPixmap().scaled(
                    32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            if pixmap:
                point = option.rect.topLeft()
                painter.drawPixmap(QPoint(point.x(), point.y() + 5), pixmap)
                option.rect = option.rect.translated(pixmap.width(), 0)
        super(Delegate, self).paint(painter, option, index)


class FilesView(QTableView):

    location_updated = Signal(str)

    def __init__(self, gui, gateway):  # pylint: disable=too-many-statements
        super().__init__()
        self.gui = gui
        self.gateway = gateway
        self.invite_sender_dialogs = []
        self._rescan_required = False
        self._restart_required = False
        self.location: str = ""

        self.source_model = FilesModel(self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterKeyColumn(self.source_model.NAME_COLUMN)
        self.proxy_model.setFilterRole(Qt.UserRole)

        self.setModel(self.proxy_model)
        self.setItemDelegate(Delegate(self))
        self.setFont(Font(12))

        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 150)
        self.setColumnWidth(2, 115)
        self.setColumnWidth(3, 80)
        self.setColumnWidth(4, 10)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.setHeaderHidden(True)
        # self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setFocusPolicy(Qt.NoFocus)
        # font = QFont()
        # font.setPointSize(12)
        self.setShowGrid(False)
        self.setIconSize(QSize(32, 32))
        self.setWordWrap(False)

        vertical_header = self.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(42)
        vertical_header.hide()

        horizontal_header = self.horizontalHeader()
        horizontal_header.setHighlightSections(False)
        horizontal_header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        horizontal_header.setFont(Font(11))
        horizontal_header.setFixedHeight(30)
        horizontal_header.setStretchLastSection(False)
        horizontal_header.setSectionResizeMode(0, QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(1, QHeaderView.Stretch)
        horizontal_header.setSectionResizeMode(2, QHeaderView.Stretch)
        # horizontal_header.setSectionResizeMode(3, QHeaderView.Stretch)
        # horizontal_header.setSectionResizeMode(4, QHeaderView.Stretch)
        # self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        # self.header().setSectionResizeMode(3, QHeaderView.Stretch)
        # self.setIconSize(QSize(24, 24))

        self.doubleClicked.connect(self.on_double_click)
        # self.customContextMenuRequested.connect(self.on_right_click)

        self.update_location(self.gateway.name)  # start in "root" directory

        self.source_model.populate()

    def update_location(self, location: str) -> None:
        self.proxy_model.setFilterRegularExpression(f"^{location}$")
        self.location = location
        self.location_updated.emit(location)
        print("location updated:", location)

    def on_double_click(self, index):
        print("on_double_click", self.location)
        print(self.proxy_model.filterRegularExpression().pattern())
        location = self.proxy_model.data(index, Qt.UserRole)
        # TODO: Update location if location is a directory, open otherwise
        text = self.proxy_model.data(index, Qt.DisplayRole)
        self.update_location(f"{location}/{text}")

        model_index = self.proxy_model.mapToSource(index)
        item = self.source_model.itemFromIndex(model_index)
        print("item:", item)

    @inlineCallbacks
    def add_folder(self, path):
        path = os.path.realpath(path)
        self.source_model.add_folder(path)
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
            self.source_model.remove_folder(folder_name)
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
            self.hide_drop_label()
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
