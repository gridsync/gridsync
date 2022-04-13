# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import QFileInfo, QSize, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAction, QFileIconProvider, QToolBar

if TYPE_CHECKING:
    from PyQt5.QtCore import QModelIndex
    from gridsync.view import View

from gridsync import config_dir, resource
from gridsync.gui.pixmap import CompositePixmap
from gridsync.magic_folder import MagicFolderStatus
from gridsync.preferences import get_preference
from gridsync.util import humanized_list


class Model(QStandardItemModel):
    def __init__(self, view: View) -> None:
        super().__init__(0, 5)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = self.gateway.monitor
        self.status_dict: dict[str, MagicFolderStatus] = {}
        self.members_dict: dict[str, list] = {}
        self._magic_folder_errors: defaultdict = defaultdict(dict)
        self.setHeaderData(0, Qt.Horizontal, "Name")
        self.setHeaderData(1, Qt.Horizontal, "Status")
        self.setHeaderData(2, Qt.Horizontal, "Last modified")
        self.setHeaderData(3, Qt.Horizontal, "Size")
        self.setHeaderData(4, Qt.Horizontal, "")

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
        self.icon_error = QIcon(resource("alert-circle-red.png"))

        self.monitor.connected.connect(self.on_connected)
        self.monitor.disconnected.connect(self.on_disconnected)
        self.monitor.check_finished.connect(self.update_natural_times)

        self.mf_monitor = self.gateway.magic_folder.monitor
        self.mf_monitor.folder_added.connect(self.add_folder)
        self.mf_monitor.folder_removed.connect(self.on_folder_removed)
        self.mf_monitor.folder_mtime_updated.connect(self.set_mtime)
        self.mf_monitor.folder_size_updated.connect(self.set_size)
        self.mf_monitor.backup_added.connect(self.add_remote_folder)
        self.mf_monitor.folder_status_changed.connect(self.set_status)
        self.mf_monitor.error_occurred.connect(self.on_error_occurred)
        self.mf_monitor.files_updated.connect(self.on_files_updated)
        self.mf_monitor.sync_progress_updated.connect(
            self.set_transfer_progress
        )

    @pyqtSlot(str, str, int)
    def on_error_occurred(
        self, folder_name: str, summary: str, timestamp: int
    ) -> None:
        self._magic_folder_errors[folder_name][summary] = timestamp

    @pyqtSlot()
    def on_connected(self) -> None:
        if get_preference("notifications", "connection") == "true":
            self.gui.show_message(
                self.gateway.name, "Connected to {}".format(self.gateway.name)
            )

    @pyqtSlot()
    def on_disconnected(self) -> None:
        if get_preference("notifications", "connection") == "true":
            self.gui.show_message(
                self.gateway.name,
                "Disconnected from {}".format(self.gateway.name),
            )

    @pyqtSlot(str, list, str, str)
    def on_updated_files(
        self, folder_name: str, files_list: list, action: str, author: str
    ) -> None:
        if get_preference("notifications", "folder") != "false":
            self.gui.show_message(
                folder_name + " folder updated",
                "{} {}".format(
                    author + " " + action if author else action.capitalize(),
                    humanized_list(files_list),
                ),
            )

    @pyqtSlot(str, list)
    def on_files_updated(self, folder_name: str, files: list) -> None:
        if get_preference("notifications", "folder") != "false":
            self.gui.show_message(
                f"{folder_name} folder updated",
                f"Updated {humanized_list(files)}",
            )

    def data(self, index: QModelIndex, role: int) -> None:
        value = super().data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path: str) -> None:
        basename = os.path.basename(os.path.normpath(path))
        if self.findItems(basename):
            logging.warning(
                "Tried to add a folder (%s) that already exists", basename
            )
            return
        composite_pixmap = CompositePixmap(self.icon_folder.pixmap(256, 256))
        name = QStandardItem(QIcon(composite_pixmap), basename)
        name.setToolTip(path)
        status = QStandardItem()
        mtime = QStandardItem()
        size = QStandardItem()
        action = QStandardItem()
        self.appendRow([name, status, mtime, size, action])
        action_bar = QToolBar()
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
        self.view.setIndexWidget(action.index(), action_bar)
        self.view.hide_drop_label()
        self.set_status(basename, MagicFolderStatus.LOADING)

    def remove_folder(self, folder_name: str) -> None:
        self.gui.systray.remove_operation((self.gateway, folder_name))
        items = self.findItems(folder_name)
        if items:
            self.removeRow(items[0].row())

    def update_folder_icon(
        self, folder_name: str, overlay_file: Optional[str] = ""
    ) -> None:
        items = self.findItems(folder_name)
        if items:
            folder_path = self.gateway.magic_folder.get_directory(folder_name)
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

    def set_status_private(self, folder_name: str) -> None:
        self.update_folder_icon(folder_name)
        items = self.findItems(folder_name)
        if items:
            items[0].setToolTip(
                "{}\n\nThis folder is private; only you can view and\nmodify "
                "its contents.".format(
                    self.gateway.magic_folder.get_directory(folder_name)
                    or folder_name + " (Stored remotely)"
                )
            )

    def set_status_shared(self, folder_name: str) -> None:
        self.update_folder_icon(folder_name, "laptop.png")
        items = self.findItems(folder_name)
        if items:
            items[0].setToolTip(
                "{}\n\nAt least one other device can view and modify\n"
                "this folder's contents.".format(
                    self.gateway.magic_folder.get_directory(folder_name)
                    or folder_name + " (Stored remotely)"
                )
            )

    def update_overlay(self, folder_name: str) -> None:
        members = self.members_dict.get(folder_name)
        if members and len(members) > 1:
            self.set_status_shared(folder_name)
        else:
            self.set_status_private(folder_name)

    @pyqtSlot(str, list)
    def on_members_updated(self, folder: str, members: list) -> None:
        self.members_dict[folder] = members
        self.update_overlay(folder)

    @staticmethod
    def _errors_to_str(errors: Dict[str, int]) -> str:
        lines = []
        for s, t in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"{s} ({datetime.fromtimestamp(t)})")
        return "\n".join(lines)

    def is_folder_syncing(self) -> bool:
        for row in range(self.rowCount()):
            if (
                self.item(row, 1).data(Qt.UserRole)
                == MagicFolderStatus.SYNCING
            ):
                return True
        return False

    @pyqtSlot(str, object)
    def set_status(self, name: str, status: MagicFolderStatus) -> None:
        items = self.findItems(name)
        if not items:
            return
        item = self.item(items[0].row(), 1)
        if status == MagicFolderStatus.LOADING:
            item.setIcon(self.icon_blank)
            item.setText("Loading...")
        elif status == MagicFolderStatus.WAITING:
            item.setIcon(self.icon_blank)
            item.setText("Waiting to scan...")
        elif status == MagicFolderStatus.SYNCING:
            item.setIcon(self.icon_blank)
            item.setText("Syncing")
            item.setToolTip(
                "This folder is syncing. New files are being uploaded or "
                "downloaded."
            )
        elif status == MagicFolderStatus.UP_TO_DATE:
            item.setIcon(self.icon_up_to_date)
            item.setText("Up to date")
            item.setToolTip(
                "This folder is up to date. The contents of this folder on\n"
                "your computer matches the contents of the folder on the\n"
                '"{}" grid.'.format(self.gateway.name)
            )
            self.update_overlay(name)
            self.unfade_row(name)
        elif status == MagicFolderStatus.STORED_REMOTELY:
            item.setIcon(self.icon_cloud)
            item.setText("Stored remotely")
            item.setToolTip(
                'This folder is stored remotely on the "{}" grid.\n'
                'Right-click and select "Download" to sync it with your '
                "local computer.".format(self.gateway.name)
            )
        elif status == MagicFolderStatus.ERROR:
            errors = self._magic_folder_errors[name]
            if errors:
                item.setIcon(self.icon_error)
                item.setText("Error syncing folder")
                item.setToolTip(self._errors_to_str(errors))
        if status == MagicFolderStatus.SYNCING:
            self.gui.systray.add_operation((self.gateway, name))
            self.gui.systray.update()
        else:
            self.gui.systray.remove_operation((self.gateway, name))
        item.setData(status, Qt.UserRole)
        self.status_dict[name] = status

    @pyqtSlot(str, object, object)
    def set_transfer_progress(
        self, folder_name: str, transferred: int, total: int
    ) -> None:
        items = self.findItems(folder_name)
        if not items:
            return
        percent_done = int(transferred / total * 100)
        if percent_done:
            item = self.item(items[0].row(), 1)
            item.setText("Syncing ({}%)".format(percent_done))

    def fade_row(
        self, folder_name: str, overlay_file: Optional[str] = ""
    ) -> None:
        try:
            folder_item = self.findItems(folder_name)[0]
        except IndexError:
            return
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

    def unfade_row(self, folder_name: str) -> None:
        folder_item = self.findItems(folder_name)[0]
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(False)
            item.setFont(font)
            item.setForeground(self.view.palette().text())

    @pyqtSlot(str, int)
    def set_mtime(self, name: str, mtime: int) -> None:
        if not mtime:
            return
        items = self.findItems(name)
        if items:
            item = self.item(items[0].row(), 2)
            item.setData(mtime, Qt.UserRole)
            item.setText(
                naturaltime(datetime.now() - datetime.fromtimestamp(mtime))
            )
            item.setToolTip("Last modified: {}".format(time.ctime(mtime)))

    @pyqtSlot(str, object)
    def set_size(self, name: str, size: int) -> None:
        items = self.findItems(name)
        if items:
            item = self.item(items[0].row(), 3)
            item.setText(naturalsize(size))
            item.setData(size, Qt.UserRole)

    @pyqtSlot()
    def update_natural_times(self) -> None:
        for i in range(self.rowCount()):
            item = self.item(i, 2)
            data = item.data(Qt.UserRole)
            if data:
                item.setText(
                    naturaltime(datetime.now() - datetime.fromtimestamp(data))
                )

    @pyqtSlot(str)
    @pyqtSlot(str, str)
    def add_remote_folder(
        self, folder_name: str, overlay_file: Optional[str] = ""
    ) -> None:
        self.add_folder(folder_name)
        self.set_status(folder_name, MagicFolderStatus.STORED_REMOTELY)
        self.fade_row(folder_name, overlay_file)

    @pyqtSlot(str)
    def on_folder_removed(self, folder_name: str) -> None:
        self.set_status(folder_name, MagicFolderStatus.STORED_REMOTELY)
        self.fade_row(folder_name)
