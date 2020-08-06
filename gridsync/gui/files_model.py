# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import QFileInfo, Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PyQt5.QtWidgets import QFileIconProvider

from gridsync import resource, config_dir
from gridsync.gui.pixmap import CompositePixmap
from gridsync.monitor import MagicFolderChecker


class FilesModel(QStandardItemModel):

    NAME_COLUMN = 0
    STATUS_COLUMN = 1
    MTIME_COLUMN = 2
    SIZE_COLUMN = 3
    ACTION_COLUMN = 4

    def __init__(self, gateway):
        super().__init__(0, 5)
        self.gateway = gateway
        self.status_dict = {}
        self.members_dict = {}

        self.setHeaderData(self.NAME_COLUMN, Qt.Horizontal, "Name")
        self.setHeaderData(self.STATUS_COLUMN, Qt.Horizontal, "Status")
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

        self.monitor = self.gateway.monitor
        self.monitor.status_updated.connect(self.set_status)
        self.monitor.mtime_updated.connect(self.set_mtime)
        self.monitor.size_updated.connect(self.set_size)
        self.monitor.members_updated.connect(self.on_members_updated)
        # self.monitor.files_updated.connect(self.on_updated_files)
        self.monitor.check_finished.connect(self.update_natural_times)
        self.monitor.remote_folder_added.connect(self.add_remote_folder)
        self.monitor.transfer_progress_updated.connect(
            self.set_transfer_progress
        )
        self.monitor.file_updated.connect(self.on_file_updated)

    def add_folder(self, path, status_data=0):
        basename = os.path.basename(os.path.normpath(path))
        if self.findItems(basename, Qt.MatchExactly, self.NAME_COLUMN):
            logging.warning(
                "Tried to add a folder (%s) that already exists", basename
            )
            return
        composite_pixmap = CompositePixmap(self.icon_folder.pixmap(256, 256))
        name = QStandardItem(QIcon(composite_pixmap), basename)
        name.setData(self.gateway.name, Qt.UserRole)
        status = QStandardItem()
        mtime = QStandardItem()
        size = QStandardItem()
        action = QStandardItem()
        self.appendRow([name, status, mtime, size, action])
        self.set_status(basename, status_data)

    @staticmethod
    def _get_file_icon(path: str, size: int = 48) -> QIcon:
        if os.path.splitext(path)[1].lower() in (
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
        ):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return QIcon(
                    pixmap.scaled(
                        size,
                        size,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
        return QFileIconProvider().icon(QFileInfo(path))

    @staticmethod
    def _set_mtime(item: QStandardItem, mtime: int) -> None:
        item.setText(
            naturaltime(datetime.now() - datetime.fromtimestamp(mtime))
        )
        item.setData(mtime, Qt.UserRole)
        item.setToolTip(f"Last modified: {time.ctime(mtime)}")

    @staticmethod
    def _set_size(item: QStandardItem, size: int) -> None:
        item.setText(naturalsize(size))
        item.setData(size, Qt.UserRole)
        item.setToolTip(f"Size: {size} bytes")

    @Slot(str, object)
    def on_file_updated(self, name, data):
        file_path = data.get("path", "").rstrip(os.path.sep)
        dirname, basename = os.path.split(file_path)
        if dirname:
            location = f"{self.gateway.name}/{name}/{dirname}"
        else:
            location = f"{self.gateway.name}/{name}"

        local_path = os.path.join(
            self.gateway.get_magic_folder_directory(name), file_path
        )

        items = self.findItems(basename, Qt.MatchExactly, self.NAME_COLUMN)
        for item in items:
            if item.data(Qt.UserRole) == location:  # file is already in model
                item.setIcon(self._get_file_icon(local_path))
                row = item.row()
                self._set_mtime(
                    self.item(row, self.MTIME_COLUMN), data.get("mtime", 0),
                )
                self._set_size(
                    self.item(row, self.SIZE_COLUMN), data.get("size", 0),
                )
                return

        name_item = QStandardItem(self._get_file_icon(local_path), basename)
        name_item.setData(location, Qt.UserRole)
        name_item.setToolTip(local_path)

        status_item = QStandardItem()

        mtime_item = QStandardItem()
        self._set_mtime(mtime_item, data.get("mtime", 0))

        size_item = QStandardItem()
        self._set_size(size_item, data.get("size", 0))

        action_item = QStandardItem()

        self.appendRow(
            [name_item, status_item, mtime_item, size_item, action_item]
        )

    def remove_folder(self, folder_name):
        self.on_sync_finished(folder_name)
        # items = self.findItems(folder_name)
        items = self.findItems(folder_name, Qt.MatchExactly, self.NAME_COLUMN)
        if items:
            self.removeRow(items[0].row())

    def populate(self):
        for magic_folder in list(self.gateway.load_magic_folders().values()):
            self.add_folder(magic_folder["directory"])

    def update_folder_icon(self, folder_name, folder_path, overlay_file=None):
        items = self.findItems(folder_name, Qt.MatchExactly, self.NAME_COLUMN)
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
        items = self.findItems(folder_name, Qt.MatchExactly, self.NAME_COLUMN)
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
        items = self.findItems(folder_name, Qt.MatchExactly, self.NAME_COLUMN)
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

    @Slot(str, list)
    def on_members_updated(self, folder, members):
        self.members_dict[folder] = members
        self.update_overlay(folder)

    @Slot(str, int)
    def set_status(self, name, status):
        items = self.findItems(name, Qt.MatchExactly, self.NAME_COLUMN)
        if not items:
            return
        item = self.item(items[0].row(), self.STATUS_COLUMN)
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

    @Slot(str, object, object)
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
        item = self.item(items[0].row(), self.STATUS_COLUMN)
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
        folder_item = self.findItems(
            folder_name, Qt.MatchExactly, self.NAME_COLUMN
        )[0]
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(False)
            item.setFont(font)
            # item.setForeground(self.view.palette().text())

    @Slot(str, int)
    def set_mtime(self, name, mtime):
        if not mtime:
            return
        items = self.findItems(name, Qt.MatchExactly, self.NAME_COLUMN)
        if items:
            item = self.item(items[0].row(), self.MTIME_COLUMN)
            item.setData(mtime, Qt.UserRole)
            item.setText(
                naturaltime(datetime.now() - datetime.fromtimestamp(mtime))
            )
            item.setToolTip("Last modified: {}".format(time.ctime(mtime)))

    @Slot(str, object)
    def set_size(self, name, size):
        items = self.findItems(name, Qt.MatchExactly, self.NAME_COLUMN)
        if items:
            item = self.item(items[0].row(), self.SIZE_COLUMN)
            item.setText(naturalsize(size))
            item.setData(size, Qt.UserRole)

    @Slot()
    def update_natural_times(self):
        for i in range(self.rowCount()):
            item = self.item(i, self.MTIME_COLUMN)
            data = item.data(Qt.UserRole)
            if data:
                item.setText(
                    naturaltime(datetime.now() - datetime.fromtimestamp(data))
                )

    @Slot(str, str)
    def add_remote_folder(self, folder_name, overlay_file=None):
        self.add_folder(folder_name, 3)
        self.fade_row(folder_name, overlay_file)
