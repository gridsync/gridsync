# -*- coding: utf-8 -*-

import os

from PyQt5.QtCore import (
    QModelIndex,
    QPoint,
    QSize,
    QRegularExpression,
    QSortFilterProxyModel,
    Qt,
)
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import (
    QHeaderView,
    QStyledItemDelegate,
    QTableView,
    QToolButton,
)

from gridsync import resource
from gridsync.gui.font import Font
from gridsync.gui.files_model import FilesModel
from gridsync.monitor import MagicFolderChecker


class ActionItemDelegate(QStyledItemDelegate):

    button_clicked = Signal(QModelIndex)

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self._button_icon = QIcon(resource("dots-horizontal-triple.png"))

    def createEditor(
        self, parent, option, index
    ):  # pylint: disable=unused-argument
        button = QToolButton(parent)
        button.setIcon(self._button_icon)
        button.setIconSize(QSize(20, 20))
        button.setToolTip("Action...")
        button.setStyleSheet("QToolButton { border: 0px }")
        button.clicked.connect(lambda: self.button_clicked.emit(index))
        return button

    def paint(self, painter, option, index):  # pylint: disable=unused-argument
        self.view.openPersistentEditor(index)


class StatusItemDelegate(QStyledItemDelegate):
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
        super().paint(painter, option, index)


class FilesView(QTableView):

    location_updated = Signal(str)
    selection_updated = Signal(list)

    def __init__(self, gui, gateway):  # pylint: disable=too-many-statements
        super().__init__()
        self.gui = gui
        self.gateway = gateway

        self.location: str = ""

        self.source_model = FilesModel(self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterKeyColumn(self.source_model.NAME_COLUMN)

        self.setModel(self.proxy_model)
        self.setItemDelegateForColumn(
            self.source_model.STATUS_COLUMN, StatusItemDelegate(self)
        )
        self.action_item_delegate = ActionItemDelegate(self)
        self.setItemDelegateForColumn(
            self.source_model.ACTION_COLUMN, self.action_item_delegate
        )
        self.setFont(Font(12))

        self.setAcceptDrops(True)
        self.setAlternatingRowColors(True)
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 150)
        self.setColumnWidth(2, 115)
        self.setColumnWidth(3, 90)
        self.setColumnWidth(4, 10)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.setHeaderHidden(True)
        # self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QTableView.NoEditTriggers)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)
        # self.setFocusPolicy(Qt.NoFocus)
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

        self.selection_model = self.selectionModel()
        self.selection_model.selectionChanged.connect(
            self.on_selection_changed
        )
        self.action_item_delegate.button_clicked.connect(
            self.on_action_button_clicked
        )

        self.update_location(self.gateway.name)  # start in "root" directory

        self.source_model.populate()

    def update_location(self, location: str) -> None:
        self.proxy_model.setFilterRole(Qt.UserRole)
        self.proxy_model.setFilterRegularExpression(f"^{location}$")
        self.location = location
        self.location_updated.emit(location)
        print("location updated:", location)

    def update_search_filter(self, text: str) -> None:
        if not text:
            self.update_location(self.location)
            return
        self.proxy_model.setFilterRole(Qt.DisplayRole)
        self.proxy_model.setFilterRegularExpression(
            QRegularExpression(text, QRegularExpression.CaseInsensitiveOption)
        )
        print("search filter updated:", text)

    def _get_name_item_from_index(self, index):
        source_index = self.proxy_model.mapToSource(index)
        source_item = self.source_model.itemFromIndex(source_index)
        row = source_item.row()
        return self.source_model.item(row, self.source_model.NAME_COLUMN)

    def on_action_button_clicked(self, index: QModelIndex) -> None:
        print(self, index, index.row())  # XXX

    def on_double_click(self, index):
        try:
            name_item = self._get_name_item_from_index(index)
        except AttributeError:
            return
        # TODO: Update location if location is a directory, open otherwise
        location = name_item.data(Qt.UserRole)
        text = name_item.text()
        self.update_location(f"{location}/{text}")

    def get_selected(self) -> list:
        selected = []
        for index in self.selection_model.selectedRows():
            item = self._get_name_item_from_index(index)
            if item:
                selected.append(
                    os.path.join(
                        item.data(Qt.UserRole), item.data(Qt.DisplayRole)
                    )
                )
        return selected

    def on_selection_changed(self, _, __):
        self.selection_updated.emit(self.get_selected())

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        event.ignore()
