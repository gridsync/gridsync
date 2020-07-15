# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import sys
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import pyqtSlot, QFileInfo, QSize, QSortFilterProxyModel, Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import QAction, QFileIconProvider, QToolBar, QLabel

from gridsync import resource, config_dir
from gridsync.gui.pixmap import CompositePixmap
from gridsync.monitor import MagicFolderChecker
from gridsync.preferences import get_preference
from gridsync.util import humanized_list


class FilesModel(QStandardItemModel):

    STATUS_COLUMN = 0
    NAME_COLUMN = 1
    MTIME_COLUMN = 2
    SIZE_COLUMN = 3
    ACTION_COLUMN = 4

    def __init__(self, view):
        super().__init__(0, 5)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = self.gateway.monitor
        self.status_dict = {}
        self.members_dict = {}
        self.grid_status = ""
        self.available_space = 0
        self.magic_folders = {}

        self.setHeaderData(self.STATUS_COLUMN, Qt.Horizontal, "Status")
        self.setHeaderData(self.NAME_COLUMN, Qt.Horizontal, "Name")
        self.setHeaderData(self.MTIME_COLUMN, Qt.Horizontal, "Last modified")
        self.setHeaderData(self.SIZE_COLUMN, Qt.Horizontal, "Size")
        self.setHeaderData(self.ACTION_COLUMN, Qt.Horizontal, "")

        self.icon_blank = QIcon()
        self.icon_up_to_date = QIcon(resource("checkmark.png"))
        self.icon_user = QIcon(resource("user.png"))
        self.icon_folder = QFileIconProvider().icon(QFileInfo(config_dir))
        composite_pixmap = CompositePixmap(
            self.icon_folder.pixmap(256, 256), overlay=None, grayout=True
        )
        self.icon_folder_gray = QIcon(composite_pixmap)
        self.icon_cloud = QIcon(resource("cloud-icon.png"))
        self.icon_action = QIcon(resource("dots-horizontal-triple.png"))

        # self.monitor.connected.connect(self.on_connected)
        # self.monitor.disconnected.connect(self.on_disconnected)
        # self.monitor.nodes_updated.connect(self.on_nodes_updated)
        self.monitor.space_updated.connect(self.on_space_updated)
        self.monitor.status_updated.connect(self.set_status)
        self.monitor.mtime_updated.connect(self.set_mtime)
        self.monitor.size_updated.connect(self.set_size)
        self.monitor.members_updated.connect(self.on_members_updated)
        self.monitor.sync_started.connect(self.on_sync_started)
        self.monitor.sync_finished.connect(self.on_sync_finished)
        # self.monitor.files_updated.connect(self.on_updated_files)
        self.monitor.check_finished.connect(self.update_natural_times)
        self.monitor.remote_folder_added.connect(self.add_remote_folder)
        self.monitor.transfer_progress_updated.connect(
            self.set_transfer_progress
        )
        self.monitor.file_updated.connect(self.on_file_updated)

    def on_space_updated(self, size):
        self.available_space = size

    def add_folder(self, path, status_data=0):
        basename = os.path.basename(os.path.normpath(path))
        # if self.findItems(basename):
        if self.findItems(basename, Qt.MatchExactly, 1):
            logging.warning(
                "Tried to add a folder (%s) that already exists", basename
            )
            return
        composite_pixmap = CompositePixmap(self.icon_folder.pixmap(256, 256))
        name = QStandardItem(QIcon(composite_pixmap), basename)
        # name.setData(self.gateway.name + ":", Qt.UserRole)
        name.setData(self.gateway.name, Qt.UserRole)
        # name.setToolTip(path)
        status = QStandardItem()
        mtime = QStandardItem()
        size = QStandardItem()
        action = QStandardItem()
        # self.appendRow([name, status, mtime, size, action])
        self.appendRow([status, name, mtime, size, action])
        action_bar = QToolBar(self.view)
        # action_bar = QToolBar(action)
        # action_bar = QToolBar(self.view.model().model)
        action_bar.setIconSize(QSize(16, 16))
        if sys.platform == "darwin":
            # See: https://bugreports.qt.io/browse/QTBUG-12717
            action_bar.setStyleSheet(
                "background-color: {0}; border: 0px {0}".format(
                    self.view.palette().base().color().name()
                )
            )
        action_bar_action = QAction(self.icon_action, "Action...", self)
        action_bar_action.setStatusTip("Action...")
        action_bar_action.triggered.connect(self.view.on_right_click)
        action_bar.addAction(action_bar_action)
        print("#################################################3")
        # print(action_bar)
        # print(action_bar.show())
        print(action.index())
        # print(action_bar.isVisible())
        print("#################################################3")
        # self.view.setIndexWidget(action.index(), action_bar)
        self.view.setIndexWidget(action.index(), QLabel("hi"))
        # self.view.hide_drop_label()
        self.set_status(basename, status_data)

    @staticmethod
    def is_image(path: str) -> bool:
        ext = os.path.splitext(path)[1]
        if ext.lower() in (".jpg", ".jpeg", ".png", ".gif"):
            return True
        return False

    def _maybe_load_thumbnail(self, item, path):
        pass

    @Slot(str, object)
    def on_file_updated(self, name, data):
        file_path = data.get("path", "")
        dirname, basename = os.path.split(file_path)
        if dirname:
            location = f"{self.gateway.name}/{name}/{dirname}"
        else:
            location = f"{self.gateway.name}/{name}"

        folder_directory = self.magic_folders[name].get("directory", "")
        full_path = os.path.join(folder_directory, file_path)
        if folder_directory and self.is_image(full_path):
            pixmap = QPixmap(os.path.join(folder_directory, file_path))
            if not pixmap.isNull():
                icon = QIcon(
                    pixmap.scaled(
                        48, 48, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                    )
                )
            else:
                icon = QFileIconProvider().icon(QFileInfo(full_path))
        else:
            icon = QFileIconProvider().icon(QFileInfo(full_path))

        name_item = QStandardItem(icon, basename)
        name_item.setToolTip(location)
        name_item.setData(location, Qt.UserRole)

        mtime = data.get("mtime", 0)
        mtime_item = QStandardItem(
            naturaltime(datetime.now() - datetime.fromtimestamp(mtime))
        )
        mtime_item.setData(mtime, Qt.UserRole)
        mtime_item.setToolTip(f"Last modified: {time.ctime(mtime)}")

        size = data.get("size", 0)
        size_item = QStandardItem(naturalsize(size))
        size_item.setData(size, Qt.UserRole)
        size_item.setToolTip(f"Size: {size} bytes")

        self.appendRow(
            [
                QStandardItem(),
                name_item,
                mtime_item,
                size_item,
                QStandardItem(),
                # QStandardItem(location),
            ]
        )

    def remove_folder(self, folder_name):
        self.on_sync_finished(folder_name)
        # items = self.findItems(folder_name)
        items = self.findItems(folder_name, Qt.MatchExactly, 1)
        if items:
            self.removeRow(items[0].row())

    def populate(self):
        for magic_folder in list(self.gateway.load_magic_folders().values()):
            self.add_folder(magic_folder["directory"])
        for name, data in self.gateway.load_magic_folders().items():
            print("#########################", data)  # XXX
            self.magic_folders[name] = data

    def update_folder_icon(self, folder_name, folder_path, overlay_file=None):
        items = self.findItems(folder_name, Qt.MatchExactly, 1)
        if items:
            if folder_path:
                folder_icon = QFileIconProvider().icon(QFileInfo(folder_path))
            else:
                folder_icon = self.icon_folder_gray
            folder_pixmap = folder_icon.pixmap(256, 256)
            if overlay_file:
                pixmap = CompositePixmap(folder_pixmap, resource(overlay_file))
            else:
                pixmap = CompositePixmap(folder_pixmap)
            items[0].setIcon(QIcon(pixmap))

    def set_status_private(self, folder_name):
        self.update_folder_icon(
            folder_name, self.gateway.get_magic_folder_directory(folder_name)
        )
        items = self.findItems(folder_name, Qt.MatchExactly, 1)
        if items:
            items[0].setToolTip(
                "{}\n\nThis folder is private; only you can view and\nmodify "
                "its contents.".format(
                    self.gateway.get_magic_folder_directory(folder_name)
                    or folder_name + " (Stored remotely)"
                )
            )

    def set_status_shared(self, folder_name):
        self.update_folder_icon(
            folder_name,
            self.gateway.get_magic_folder_directory(folder_name),
            "laptop.png",
        )
        items = self.findItems(folder_name, Qt.MatchExactly, 1)
        if items:
            items[0].setToolTip(
                "{}\n\nAt least one other device can view and modify\n"
                "this folder's contents.".format(
                    self.gateway.get_magic_folder_directory(folder_name)
                    or folder_name + " (Stored remotely)"
                )
            )

    def update_overlay(self, folder_name):
        members = self.members_dict.get(folder_name)
        if members and len(members) > 1:
            self.set_status_shared(folder_name)
        else:
            self.set_status_private(folder_name)

    @pyqtSlot(str, list)
    def on_members_updated(self, folder, members):
        self.members_dict[folder] = members
        self.update_overlay(folder)

    @pyqtSlot(str, int)
    def set_status(self, name, status):
        items = self.findItems(name, Qt.MatchExactly, 1)
        if not items:
            return
        # item = self.item(items[0].row(), 1)
        item = self.item(items[0].row(), 0)
        if status == MagicFolderChecker.LOADING:
            item.setIcon(self.icon_blank)
            item.setText("Loading...")
        elif status in (
            MagicFolderChecker.SYNCING,
            MagicFolderChecker.SCANNING,
        ):
            item.setIcon(self.icon_blank)
            item.setText("Syncing")
            item.setToolTip(
                "This folder is syncing. New files are being uploaded or "
                "downloaded."
            )
        elif status == MagicFolderChecker.UP_TO_DATE:
            item.setIcon(self.icon_up_to_date)
            item.setText("Up to date")
            item.setToolTip(
                "This folder is up to date. The contents of this folder on\n"
                "your computer matches the contents of the folder on the\n"
                '"{}" grid.'.format(self.gateway.name)
            )
            self.update_overlay(name)
            self.unfade_row(name)
        elif status == 3:
            item.setIcon(self.icon_cloud)
            item.setText("Stored remotely")
            item.setToolTip(
                'This folder is stored remotely on the "{}" grid.\n'
                'Right-click and select "Download" to sync it with your '
                "local computer.".format(self.gateway.name)
            )
        item.setData(status, Qt.UserRole)
        self.status_dict[name] = status

    @pyqtSlot(str, object, object)
    def set_transfer_progress(self, folder_name, transferred, total):
        items = self.findItems(folder_name)
        if not items:
            return
        percent_done = int(transferred / total * 100)
        if not percent_done:
            # Magic-folder's periodic "full scan" (which occurs every 10
            # minutes) temporarily adds *all* known files to the queue
            # exposed by the "status" API for a very brief period (seemingly
            # for only a second or two). Because of this -- and since we rely
            # on the magic-folder "status" API to tell us information about
            # current and pending transfers to calculate total progress --
            # existing "syncing" operations will briefly display a progress
            # of "0%" during this time (since the number of bytes to be
            # transferred briefly becomes equal to the total size of the
            # entire folder -- even though those transfers do not occur and
            # vanish from the queue as soon as the the "full scan" is
            # completed). To compensate for this strange (and rare) event --
            # and because it's probably jarring to the end-user to see
            # progress dip down to "0%" for a brief moment before returning to
            # normal -- we ignore any updates to "0" here (on the assumption
            # that it's better to have a couple of seconds of no progress
            # updates than a progress update which is wrong or misleading).
            return
        item = self.item(items[0].row(), 1)
        item.setText("Syncing ({}%)".format(percent_done))

    def fade_row(self, folder_name, overlay_file=None):
        folder_item = self.findItems(folder_name)[0]
        if overlay_file:
            folder_pixmap = self.icon_folder_gray.pixmap(256, 256)
            pixmap = CompositePixmap(folder_pixmap, resource(overlay_file))
            folder_item.setIcon(QIcon(pixmap))
        else:
            folder_item.setIcon(self.icon_folder_gray)
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
            item.setForeground(QColor("gray"))

    def unfade_row(self, folder_name):
        folder_item = self.findItems(folder_name, Qt.MatchExactly, 1)[0]
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(False)
            item.setFont(font)
            item.setForeground(self.view.palette().text())

    @pyqtSlot(str)
    def on_sync_started(self, folder_name):
        self.gui.core.operations.append((self.gateway, folder_name))
        self.gui.systray.update()

    @pyqtSlot(str)
    def on_sync_finished(self, folder_name):
        try:
            self.gui.core.operations.remove((self.gateway, folder_name))
        except ValueError:
            pass

    @pyqtSlot(str, int)
    def set_mtime(self, name, mtime):
        if not mtime:
            return
        items = self.findItems(name, Qt.MatchExactly, 1)
        if items:
            item = self.item(items[0].row(), 2)
            item.setData(mtime, Qt.UserRole)
            item.setText(
                naturaltime(datetime.now() - datetime.fromtimestamp(mtime))
            )
            item.setToolTip("Last modified: {}".format(time.ctime(mtime)))

    @pyqtSlot(str, object)
    def set_size(self, name, size):
        items = self.findItems(name, Qt.MatchExactly, 1)
        if items:
            item = self.item(items[0].row(), 3)
            item.setText(naturalsize(size))
            item.setData(size, Qt.UserRole)

    @pyqtSlot()
    def update_natural_times(self):
        for i in range(self.rowCount()):
            item = self.item(i, 2)
            data = item.data(Qt.UserRole)
            if data:
                item.setText(
                    naturaltime(datetime.now() - datetime.fromtimestamp(data))
                )

    @pyqtSlot(str, str)
    def add_remote_folder(self, folder_name, overlay_file=None):
        self.add_folder(folder_name, 3)
        self.fade_row(folder_name, overlay_file)


class FilesProxyModel(QSortFilterProxyModel):
    def __init__(self, view):
        super().__init__()
        self.model = FilesModel(view)
        self.setSourceModel(self.model)

    def populate(self):
        self.model.populate()
