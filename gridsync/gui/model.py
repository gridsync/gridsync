# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import sys
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import pyqtSlot, QFileInfo, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAction, QFileIconProvider, QToolBar

from gridsync import resource, config_dir
from gridsync.gui.widgets import CompositePixmap
from gridsync.preferences import get_preference
from gridsync.util import humanized_list


class Model(QStandardItemModel):
    def __init__(self, view):
        super(Model, self).__init__(0, 5)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = self.gateway.monitor
        self.status_dict = {}
        self.members_dict = {}
        self.grid_status = ''
        self.available_space = 0
        self.setHeaderData(0, Qt.Horizontal, "Name")
        self.setHeaderData(1, Qt.Horizontal, "Status")
        self.setHeaderData(2, Qt.Horizontal, "Last modified")
        self.setHeaderData(3, Qt.Horizontal, "Size")
        self.setHeaderData(4, Qt.Horizontal, "")

        self.icon_blank = QIcon()
        self.icon_up_to_date = QIcon(resource('checkmark.png'))
        self.icon_user = QIcon(resource('user.png'))
        self.icon_folder = QFileIconProvider().icon(QFileInfo(config_dir))
        composite_pixmap = CompositePixmap(
            self.icon_folder.pixmap(256, 256), overlay=None, grayout=True)
        self.icon_folder_gray = QIcon(composite_pixmap)
        self.icon_cloud = QIcon(resource('cloud-icon.png'))
        self.icon_action = QIcon(resource('dots-horizontal-triple.png'))

        self.monitor.connected.connect(self.on_connected)
        self.monitor.disconnected.connect(self.on_disconnected)
        self.monitor.nodes_updated.connect(self.on_nodes_updated)
        self.monitor.space_updated.connect(self.on_space_updated)
        self.monitor.status_updated.connect(self.set_status)
        self.monitor.mtime_updated.connect(self.set_mtime)
        self.monitor.size_updated.connect(self.set_size)
        self.monitor.members_updated.connect(self.on_members_updated)
        self.monitor.sync_started.connect(self.on_sync_started)
        self.monitor.sync_finished.connect(self.on_sync_finished)
        self.monitor.files_updated.connect(self.on_updated_files)
        self.monitor.check_finished.connect(self.update_natural_times)
        self.monitor.remote_folder_added.connect(self.add_remote_folder)

        # XXX Temporarily(?) disabled due to magic-folder queue/status bugs
        #self.monitor.transfer_progress_updated.connect(
        #    self.set_transfer_progress)

    def on_space_updated(self, size):
        self.available_space = size

    @pyqtSlot(int, int)
    def on_nodes_updated(self, num_connected, num_happy):
        if num_connected < num_happy:
            self.grid_status = "Connecting ({}/{} nodes){}".format(
                num_connected,
                num_happy,
                (" via Tor..." if self.gateway.use_tor else "...")
            )
        elif num_connected >= num_happy:
            self.grid_status = "Connected to {} {}{} {} available".format(
                num_connected,
                'storage ' + ('node' if num_connected == 1 else 'nodes'),
                (" via Tor;" if self.gateway.use_tor else ";"),
                naturalsize(self.available_space)
            )
        self.gui.main_window.set_current_grid_status()  # TODO: Use pyqtSignal?

    @pyqtSlot()
    def on_connected(self):
        if get_preference('notifications', 'connection') != 'false':
            self.gui.show_message(
                self.gateway.name, "Connected to {}".format(self.gateway.name))

    @pyqtSlot()
    def on_disconnected(self):
        if get_preference('notifications', 'connection') != 'false':
            self.gui.show_message(
                self.gateway.name,
                "Disconnected from {}".format(self.gateway.name)
            )

    @pyqtSlot(str, list, str, str)
    def on_updated_files(self, folder_name, files_list, action, author):
        if get_preference('notifications', 'folder') != 'false':
            self.gui.show_message(
                folder_name + " folder updated",
                "{} {}".format(
                    author + " " + action if author else action.capitalize(),
                    humanized_list(files_list)
                )
            )

    def data(self, index, role):
        value = super(Model, self).data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path, status_data=0):
        basename = os.path.basename(os.path.normpath(path))
        if self.findItems(basename):
            logging.warning(
                "Tried to add a folder (%s) that already exists", basename)
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
        if sys.platform == 'darwin':
            # See: https://bugreports.qt.io/browse/QTBUG-12717
            action_bar.setStyleSheet(
                'background-color: white; border: 0px white')
        action_bar_action = QAction(self.icon_action, "Action...", self)
        action_bar_action.setStatusTip("Action...")
        action_bar_action.triggered.connect(self.view.on_right_click)
        action_bar.addAction(action_bar_action)
        self.view.setIndexWidget(action.index(), action_bar)
        self.view.hide_drop_label()
        self.set_status(basename, status_data)

    def populate(self):
        for magic_folder in list(self.gateway.load_magic_folders().values()):
            self.add_folder(magic_folder['directory'])

    def update_folder_icon(self, folder_name, folder_path, overlay_file=None):
        items = self.findItems(folder_name)
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
            folder_name, self.gateway.get_magic_folder_directory(folder_name))
        items = self.findItems(folder_name)
        if items:
            items[0].setToolTip(
                "{}\n\nThis folder is private; only you can view and\nmodify "
                "its contents.".format(
                    self.gateway.get_magic_folder_directory(folder_name)
                    or folder_name + " (Stored remotely)"))

    def set_status_shared(self, folder_name):
        self.update_folder_icon(
            folder_name,
            self.gateway.get_magic_folder_directory(folder_name),
            'user.png')
        items = self.findItems(folder_name)
        if items:
            items[0].setToolTip(
                "{}\n\nThis folder is shared; at least one other person\nor "
                "device can view and modify its contents.".format(
                    self.gateway.get_magic_folder_directory(folder_name)
                    or folder_name + " (Stored remotely)"))

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
        items = self.findItems(name)
        if not items:
            return
        item = self.item(items[0].row(), 1)
        if not status:
            item.setIcon(self.icon_blank)
            item.setText("Loading...")
        elif status == 1:
            item.setIcon(self.icon_blank)
            item.setText("Syncing")
            item.setToolTip(
                "This folder is syncing. New files are being uploaded or "
                "downloaded.")
        elif status == 2:
            item.setIcon(self.icon_up_to_date)
            item.setText("Up to date")
            item.setToolTip(
                'This folder is up to date. The contents of this folder on\n'
                'your computer matches the contents of the folder on the\n'
                '"{}" grid.'.format(self.gateway.name))
            self.update_overlay(name)
            self.unfade_row(name)
        elif status == 3:
            item.setIcon(self.icon_cloud)
            item.setText("Stored remotely")
            item.setToolTip(
                'This folder is stored remotely on the "{}" grid.\n'
                'Right-click and select "Download" to sync it with your '
                'local computer.'.format(self.gateway.name))
        elif status == 99:
            item.setIcon(self.icon_blank)
            item.setText("Scanning")
            item.setToolTip(
                "This folder is being scanned for changes.")
        item.setData(status, Qt.UserRole)
        self.status_dict[name] = status

    @pyqtSlot(str, object, object)
    def set_transfer_progress(self, folder_name, transferred, total):
        items = self.findItems(folder_name)
        if not items:
            return
        item = self.item(items[0].row(), 1)
        item.setText("Syncing ({}%)".format(
            # XXX The magic-folder status queue will sometimes display transfer
            # progresses as exceeding 100%. Cap it at 100% in the UI for now.
            min(100, int(transferred / total * 100))))

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
            item.setForeground(QColor('gray'))

    def unfade_row(self, folder_name):
        default_foreground = QStandardItem().foreground()
        folder_item = self.findItems(folder_name)[0]
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(False)
            item.setFont(font)
            item.setForeground(default_foreground)

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
        item = self.item(self.findItems(name)[0].row(), 2)
        item.setData(mtime, Qt.UserRole)
        item.setText(
            naturaltime(datetime.now() - datetime.fromtimestamp(mtime)))
        item.setToolTip("Last modified: {}".format(time.ctime(mtime)))

    @pyqtSlot(str, object)
    def set_size(self, name, size):
        item = self.item(self.findItems(name)[0].row(), 3)
        item.setText(naturalsize(size))
        item.setData(size, Qt.UserRole)

    @pyqtSlot()
    def update_natural_times(self):
        for i in range(self.rowCount()):
            item = self.item(i, 2)
            data = item.data(Qt.UserRole)
            if data:
                item.setText(
                    naturaltime(datetime.now() - datetime.fromtimestamp(data)))

    @pyqtSlot(str, str)
    def add_remote_folder(self, folder_name, overlay_file=None):
        self.add_folder(folder_name, 3)
        self.fade_row(folder_name, overlay_file)
