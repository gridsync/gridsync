# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
import os
import time

from humanize import naturalsize, naturaltime
from PyQt5.QtCore import (
    pyqtSlot, QEvent, QItemSelectionModel, QFileInfo, QPoint,
    QPropertyAnimation, QSize, Qt, QThread)
from PyQt5.QtGui import (
    QColor, QFont, QIcon, QKeySequence, QMovie, QPixmap, QStandardItem,
    QStandardItemModel)
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QComboBox, QFileDialog, QFileIconProvider,
    QGridLayout, QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox,
    QProgressDialog, QPushButton, QShortcut, QSizePolicy, QSpacerItem,
    QStackedWidget, QStyledItemDelegate, QToolButton, QTreeView, QWidget)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir
from gridsync.crypto import Crypter
from gridsync.desktop import open_folder
from gridsync.gui.password import PasswordDialog
from gridsync.gui.setup import SetupForm
from gridsync.gui.widgets import (
    CompositePixmap, InviteReceiver, PreferencesWidget, ShareWidget)
from gridsync.monitor import Monitor
from gridsync.preferences import get_preference
from gridsync.util import humanized_list


class ComboBox(QComboBox):
    def __init__(self):
        super(ComboBox, self).__init__()
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.current_index = 0

        self.activated.connect(self.on_activated)

    def on_activated(self, index):
        if index == self.count() - 1:  # If "Add new..." is selected
            self.setCurrentIndex(self.current_index)
        else:
            self.current_index = index

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            basename = os.path.basename(os.path.normpath(gateway.nodedir))
            icon = QIcon(os.path.join(gateway.nodedir, 'icon'))
            if not icon.availableSizes():
                icon = QIcon(resource('tahoe-lafs.png'))
            self.addItem(icon, basename, gateway)
        self.insertSeparator(self.count())
        self.addItem(" Add new...")


class Model(QStandardItemModel):
    def __init__(self, view):
        super(Model, self).__init__(0, 4)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = Monitor(self.gateway)
        self.status_dict = {}
        self.grid_status = ''
        self.available_space = 0
        self.setHeaderData(0, Qt.Horizontal, "Name")
        self.setHeaderData(1, Qt.Horizontal, "Status")
        self.setHeaderData(2, Qt.Horizontal, "Last modified")
        self.setHeaderData(3, Qt.Horizontal, "Size")
        #self.setHeaderData(4, Qt.Horizontal, "Action")

        self.icon_blank = QIcon()
        self.icon_up_to_date = QIcon(resource('checkmark.png'))
        self.icon_user = QIcon(resource('user.png'))
        self.icon_folder = QFileIconProvider().icon(QFileInfo(config_dir))
        composite_pixmap = CompositePixmap(
            self.icon_folder.pixmap(256, 256), overlay=None, grayout=True)
        self.icon_folder_gray = QIcon(composite_pixmap)

        self.monitor.connected.connect(self.on_connected)
        self.monitor.disconnected.connect(self.on_disconnected)
        self.monitor.nodes_updated.connect(self.on_nodes_updated)
        self.monitor.space_updated.connect(self.on_space_updated)
        self.monitor.data_updated.connect(self.set_data)
        self.monitor.status_updated.connect(self.set_status)
        self.monitor.mtime_updated.connect(self.set_mtime)
        self.monitor.size_updated.connect(self.set_size)
        #self.monitor.member_added.connect(self.add_member)  # XXX
        self.monitor.first_sync_started.connect(self.on_first_sync)
        self.monitor.sync_started.connect(self.on_sync_started)
        self.monitor.sync_finished.connect(self.on_sync_finished)
        self.monitor.files_updated.connect(self.on_updated_files)
        self.monitor.check_finished.connect(self.update_natural_times)
        self.monitor.remote_folder_added.connect(self.add_remote_folder)

    def on_space_updated(self, size):
        self.available_space = size

    @pyqtSlot(int, int)
    def on_nodes_updated(self, num_connected, num_happy):
        if num_connected < num_happy:
            self.grid_status = "Connecting ({}/{} nodes)...".format(
                num_connected, num_happy)
        elif num_connected >= num_happy:
            obj = ('node' if num_connected == 1 else 'nodes')
            self.grid_status = "Connected to {} {}; {} available".format(
                num_connected, obj, naturalsize(self.available_space))
        self.gui.main_window.set_current_grid_status()  # TODO: Use pyqtSignal?

    @pyqtSlot(str)
    def on_connected(self, grid_name):
        if get_preference('notifications', 'connection') != 'false':
            self.gui.show_message(
                grid_name, "Connected to {}".format(grid_name))

    @pyqtSlot(str)
    def on_disconnected(self, grid_name):
        if get_preference('notifications', 'connection') != 'false':
            self.gui.show_message(
                grid_name, "Disconnected from {}".format(grid_name))

    @pyqtSlot(str, list)
    def on_updated_files(self, folder_name, files_list):
        if get_preference('notifications', 'folder') != 'false':
            self.gui.show_message(
                folder_name + " updated and encrypted",
                "Updated " + humanized_list(files_list))

    def data(self, index, role):
        value = super(Model, self).data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path, name_data=None, status_data=0):
        basename = os.path.basename(os.path.normpath(path))
        if self.findItems(basename):
            logging.warning(
                "Tried to add a folder (%s) that already exists", basename)
            return
        composite_pixmap = CompositePixmap(self.icon_folder.pixmap(256, 256))
        name = QStandardItem(QIcon(composite_pixmap), basename)
        name.setData(name_data, Qt.UserRole)
        name.setToolTip(path)
        status = QStandardItem()
        mtime = QStandardItem()
        size = QStandardItem()
        self.appendRow([name, status, mtime, size])
        self.view.hide_drop_label()
        self.set_status(basename, status_data)

    @pyqtSlot(str, str)
    def add_member(self, folder, member):
        items = self.findItems(folder)
        if items:
            items[0].appendRow([QStandardItem(self.icon_user, member)])

    def populate(self):
        for magic_folder in list(self.gateway.load_magic_folders().values()):
            self.add_folder(magic_folder['directory'])
        self.monitor.start()

    def update_folder_icon(self, folder_name, folder_path, overlay_file=None):
        items = self.findItems(folder_name)
        if items:
            folder_icon = QFileIconProvider().icon(QFileInfo(folder_path))
            folder_pixmap = folder_icon.pixmap(256, 256)
            if overlay_file:
                pixmap = CompositePixmap(folder_pixmap, resource(overlay_file))
            else:
                pixmap = CompositePixmap(folder_pixmap)
            items[0].setIcon(QIcon(pixmap))

    @pyqtSlot(str, object)
    def set_data(self, folder_name, data):
        items = self.findItems(folder_name)
        if items:
            items[0].setData(data, Qt.UserRole)

    @pyqtSlot(str, int)
    def set_status(self, name, status):
        items = self.findItems(name)
        if not items:
            return
        item = self.item(items[0].row(), 1)
        if not status:
            item.setIcon(self.icon_blank)
            item.setText("Initializing...")
        elif status == 1:
            item.setIcon(self.icon_blank)
            item.setText("Syncing")
        elif status == 2:
            item.setIcon(self.icon_up_to_date)
            item.setText("Up to date")
        item.setData(status, Qt.UserRole)
        self.status_dict[name] = status

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
    def on_first_sync(self, folder_name):
        self.unfade_row(folder_name)
        self.update_folder_icon(
            folder_name, self.gateway.get_magic_folder_directory(folder_name))

    @pyqtSlot(str)
    def on_sync_started(self, folder_name):
        self.gui.core.operations.append((self.gateway, folder_name))
        self.gui.systray.update()

    @pyqtSlot(str)
    def on_sync_finished(self, folder_name):
        self.gui.core.operations.remove((self.gateway, folder_name))
        self.update_folder_icon(
            folder_name,
            self.gateway.get_magic_folder_directory(folder_name),
            'lock-closed-green.svg')

    @pyqtSlot(str, int)
    def set_mtime(self, name, mtime):
        item = self.item(self.findItems(name)[0].row(), 2)
        item.setData(mtime, Qt.UserRole)
        item.setText(
            naturaltime(datetime.now() - datetime.fromtimestamp(mtime)))
        item.setToolTip("Last modified: {}".format(time.ctime(mtime)))

    @pyqtSlot(str, int)
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

    @pyqtSlot(str, dict, str)
    def add_remote_folder(self, folder_name, caps, overlay_file=None):
        self.add_folder(folder_name, caps, 3)
        self.fade_row(folder_name, overlay_file)


class Delegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(Delegate, self).__init__(parent=None)
        self.parent = parent
        self.waiting_movie = QMovie(resource('waiting.gif'))
        self.waiting_movie.setCacheMode(True)
        self.waiting_movie.frameChanged.connect(self.on_frame_changed)
        self.sync_movie = QMovie(resource('sync.gif'))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self):
        values = self.parent.model().status_dict.values()
        if 0 in values or 1 in values:
            self.parent.viewport().update()
        else:
            self.waiting_movie.setPaused(True)
            self.sync_movie.setPaused(True)

    def paint(self, painter, option, index):
        column = index.column()
        if column == 1:
            pixmap = None
            status = index.data(Qt.UserRole)
            if not status:  # "Initializing..."
                self.waiting_movie.setPaused(False)
                pixmap = self.waiting_movie.currentPixmap().scaled(20, 20)
            elif status == 1:  # "Syncing"
                self.sync_movie.setPaused(False)
                pixmap = self.sync_movie.currentPixmap().scaled(20, 20)
            if pixmap:
                point = option.rect.topLeft()
                painter.drawPixmap(QPoint(point.x(), point.y() + 5), pixmap)
                option.rect = option.rect.translated(pixmap.width(), 0)
        super(Delegate, self).paint(painter, option, index)


class View(QTreeView):
    def __init__(self, gui, gateway):  # pylint: disable=too-many-statements
        super(View, self).__init__()
        self.gui = gui
        self.gateway = gateway
        self.share_widgets = []
        self.setModel(Model(self))
        self.setItemDelegate(Delegate(self))

        self.setAcceptDrops(True)
        #self.setColumnWidth(0, 150)
        #self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 75)
        #self.setColumnWidth(4, 50)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setFocusPolicy(Qt.NoFocus)
        #font = QFont()
        #font.setPointSize(12)
        #self.header().setFont(font)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.setIconSize(QSize(24, 24))

        self.drop_outline = QLabel(self)
        self.drop_outline.setPixmap(QPixmap(resource('drop_zone_outline.png')))
        self.drop_outline.setScaledContents(True)
        self.drop_outline.setAcceptDrops(True)
        self.drop_outline.installEventFilter(self)

        self.drop_icon = QLabel(self)
        self.drop_icon.setPixmap(QPixmap(resource('upload.png')))
        self.drop_icon.setAlignment(Qt.AlignCenter)
        self.drop_icon.setAcceptDrops(True)
        self.drop_icon.installEventFilter(self)

        self.drop_text = QLabel(self)
        self.drop_text.setText("Drop folders here")
        drop_text_font = QFont()
        drop_text_font.setPointSize(14)
        self.drop_text.setFont(drop_text_font)
        self.drop_text.setStyleSheet('color: grey')
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setAcceptDrops(True)
        self.drop_text.installEventFilter(self)
        self.drop_text.setSizePolicy(QSizePolicy.Expanding, 0)

        self.drop_subtext = QLabel(self)
        self.drop_subtext.setText("Added folders will sync automatically")
        self.drop_subtext.setStyleSheet('color: grey')
        self.drop_subtext.setAlignment(Qt.AlignCenter)
        self.drop_subtext.setAcceptDrops(True)
        self.drop_subtext.installEventFilter(self)
        self.drop_subtext.setSizePolicy(QSizePolicy.Expanding, 0)

        self.select_folder_button = QPushButton("Select...", self)
        self.select_folder_button.setAcceptDrops(True)
        self.select_folder_button.installEventFilter(self)
        self.select_folder_button.clicked.connect(self.select_folder)

        layout = QGridLayout(self)
        layout.addWidget(self.drop_outline, 1, 1, 9, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 1, 1)
        layout.addWidget(self.drop_icon, 2, 2, 3, 1)
        layout.addWidget(self.drop_text, 6, 1, 1, 3)
        layout.addWidget(self.drop_subtext, 7, 1, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 8, 1)
        layout.addWidget(self.select_folder_button, 8, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 8, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 9, 1)

        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.model().populate()

    def show_drop_label(self, _=None):
        if not self.model().rowCount():
            self.setHeaderHidden(True)
            self.drop_outline.show()
            self.drop_icon.show()
            self.drop_text.show()
            self.drop_subtext.show()
            self.select_folder_button.show()

    def hide_drop_label(self):
        self.setHeaderHidden(False)
        self.drop_outline.hide()
        self.drop_icon.hide()
        self.drop_text.hide()
        self.drop_subtext.hide()
        self.select_folder_button.hide()

    def on_double_click(self, index):
        item = self.model().itemFromIndex(index)
        if item.column() == 0:
            name = item.text()
            if name in self.gateway.magic_folders:
                open_folder(self.gateway.magic_folders[name]['directory'])

    def open_share_widget(self, folder_name):
        share_widget = ShareWidget(self.gateway, self.gui, folder_name)
        self.share_widgets.append(share_widget)  # TODO: Remove on close
        share_widget.show()

    def select_download_location(self, folders):
        dest = QFileDialog.getExistingDirectory(
            self, "Select a download destination", os.path.expanduser('~'))
        if not dest:
            return
        for folder in folders:
            data = self.model().findItems(folder)[0].data(Qt.UserRole)
            join_code = "{}+{}".format(data['collective'], data['personal'])
            path = os.path.join(dest, folder)
            self.gateway.create_magic_folder(path, join_code)  # XXX

    def confirm_remove(self, folders):
        humanized_folders = humanized_list(folders, "folders")
        title = "Remove {}?".format(humanized_folders)
        if len(folders) == 1:
            text = ("Are you sure you wish to remove the '{}' folder? If "
                    "you do, it will remain on your computer, however, {} "
                    "will no longer synchronize its contents with {}".format(
                        folders[0], APP_NAME, self.gateway.name))
        else:
            text = ("Are you sure you wish to remove {}? If you do, they "
                    "will remain on your computer, however, {} will no "
                    "longer synchronize their contents with {}.".format(
                        humanized_folders, APP_NAME, self.gateway.name))
        reply = QMessageBox.question(
            self, title, text, QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply == QMessageBox.Yes:
            for folder in folders:
                self.gateway.remove_magic_folder(folder)
                self.model().removeRow(self.model().findItems(folder)[0].row())
            d = self.model().monitor.scan_rootcap()
            d.addCallback(self.show_drop_label)

    def open_folders(self, folders):
        for folder in folders:
            folder_info = self.gateway.magic_folders.get(folder)
            if folder_info:
                open_folder(folder_info['directory'])

    def deselect_local_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect)

    def deselect_remote_folders(self):
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                folder = self.model().item(item.row(), 0).text()
                if not self.gateway.magic_folders.get(folder):
                    self.selectionModel().select(
                        index, QItemSelectionModel.Deselect)

    def get_selected_folders(self):
        folders = []
        selected = self.selectedIndexes()
        if selected:
            for index in selected:
                item = self.model().itemFromIndex(index)
                if item.column() == 0:
                    folders.append(item.text())
        return folders

    def on_right_click(self, position):
        cur_item = self.model().itemFromIndex(self.indexAt(position))
        if not cur_item:
            return
        cur_folder = self.model().item(cur_item.row(), 0).text()

        if self.gateway.magic_folders.get(cur_folder):  # is local folder
            selection_is_remote = False
            self.deselect_remote_folders()
        else:
            selection_is_remote = True
            self.deselect_local_folders()

        selected = self.get_selected_folders()

        menu = QMenu()
        if selection_is_remote:
            download_action = QAction(
                QIcon(resource('download.png')), "Download...")
            download_action.triggered.connect(
                lambda: self.select_download_location(selected))
            menu.addAction(download_action)
            menu.addSeparator()
        open_action = QAction("Open")
        open_action.triggered.connect(
            lambda: self.open_folders(selected))
        share_action = QAction(QIcon(resource('share.png')), "Share...")
        share_action.triggered.connect(
            lambda: self.open_share_widget(selected))
        remove_action = QAction(QIcon(resource('close.png')), "Remove...")
        remove_action.triggered.connect(
            lambda: self.confirm_remove(selected))
        menu.addAction(open_action)
        menu.addAction(share_action)
        menu.addSeparator()
        menu.addAction(remove_action)
        if selection_is_remote:
            open_action.setEnabled(False)
            share_action.setEnabled(False)
        menu.exec_(self.viewport().mapToGlobal(position))

    def add_new_folder(self, path):
        self.hide_drop_label()
        self.model().add_folder(path)
        self.gateway.create_magic_folder(path)

    def select_folder(self):
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            for folder in dialog.selectedFiles():
                self.add_new_folder(folder)

    def dragEnterEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()

    def dragLeaveEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        event.accept()

    def dragMoveEvent(self, event):  # pylint: disable=no-self-use
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()

    def dropEvent(self, event):
        logging.debug(event)
        if event.mimeData().hasUrls:
            event.accept()
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    self.add_new_folder(path)
                else:
                    QMessageBox.critical(
                        self, "Cannot add {}.".format(path),
                        "Cannot add '{}'.\n\n{} currently only supports "
                        "uploading and syncing folders, and not individual "
                        "files. Please try again.".format(path, APP_NAME))

    def eventFilter(self, obj, event):  # pylint: disable=unused-argument
        if event.type() == QEvent.DragEnter:
            self.dragEnterEvent(event)
            return True
        elif event.type() == QEvent.DragLeave:
            self.dragLeaveEvent(event)
            return True
        elif event.type() == QEvent.DragMove:
            self.dragMoveEvent(event)
            return True
        elif event.type() == QEvent.Drop:
            self.dropEvent(event)
            return True
        return False


class CentralWidget(QStackedWidget):
    def __init__(self, gui):
        super(CentralWidget, self).__init__()
        self.gui = gui
        self.views = []

    def clear(self):
        for _ in range(self.count()):
            self.removeWidget(self.currentWidget())

    def add_view_widget(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.addWidget(view)
        self.addWidget(widget)
        self.views.append(view)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            self.add_view_widget(gateway)


class MainWindow(QMainWindow):
    def __init__(self, gui):
        super(MainWindow, self).__init__()
        self.gui = gui
        self.gateways = []
        self.progress = None
        self.animation = None
        self.crypter = None
        self.crypter_thread = None
        self.export_data = None
        self.export_dest = None
        self.setup_form = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(500, 300))

        self.shortcut_new = QShortcut(QKeySequence.New, self)
        self.shortcut_new.activated.connect(self.show_setup_form)

        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.select_folder)

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.confirm_quit)

        self.combo_box = ComboBox()
        self.combo_box.activated[int].connect(self.on_grid_selected)

        self.central_widget = CentralWidget(self.gui)
        self.setCentralWidget(self.central_widget)

        invite_action = QAction(
            QIcon(resource('invite.png')), 'Enter an Invite Code...', self)
        invite_action.setStatusTip('Enter an Invite Code...')
        invite_action.triggered.connect(self.open_invite_receiver)

        folder_icon_default = QFileIconProvider().icon(QFileInfo(config_dir))
        folder_icon_composite = CompositePixmap(
            folder_icon_default.pixmap(256, 256), resource('green-plus.png'))
        folder_icon = QIcon(folder_icon_composite)

        folder_action = QAction(folder_icon, "Add folder...", self)
        folder_action.setStatusTip("Add folder...")

        folder_from_local_action = QAction(
            QIcon(resource('laptop.png')), "From local computer...", self)
        folder_from_local_action.setStatusTip("Add folder from local computer")
        folder_from_local_action.setToolTip("Add folder from local computer")
        #self.from_local_action.setShortcut(QKeySequence.Open)
        folder_from_local_action.triggered.connect(self.select_folder)

        folder_from_invite_action = QAction(
            QIcon(resource('invite.png')), "From Invite Code...", self)
        folder_from_invite_action.setStatusTip("Add folder from Invite Code")
        folder_from_invite_action.setToolTip("Add folder from Invite Code")
        folder_from_invite_action.triggered.connect(self.open_invite_receiver)

        folder_menu = QMenu(self)
        folder_menu.addAction(folder_from_local_action)
        folder_menu.addAction(folder_from_invite_action)

        folder_button = QToolButton(self)
        folder_button.setDefaultAction(folder_action)
        folder_button.setMenu(folder_menu)
        folder_button.setPopupMode(2)
        folder_button.setStyleSheet(
            'QToolButton::menu-indicator { image: none }')

        pair_action = QAction(
            QIcon(resource('laptop.png')), 'Connect another device...', self)
        pair_action.setStatusTip('Connect another device...')
        pair_action.triggered.connect(self.open_pair_widget)

        export_action = QAction(
            QIcon(resource('export.png')), 'Export Recovery Key', self)
        export_action.setStatusTip('Export Recovery Key...')
        export_action.setShortcut(QKeySequence.Save)
        export_action.triggered.connect(self.export_recovery_key)

        preferences_action = QAction(
            QIcon(resource('preferences.png')), 'Preferences', self)
        preferences_action.setStatusTip('Preferences')
        preferences_action.setShortcut(QKeySequence.Preferences)
        preferences_action.triggered.connect(self.toggle_preferences_widget)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        self.toolbar = self.addToolBar('')
        #self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        #self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.toolbar.addWidget(folder_button)
        #self.toolbar.addAction(invite_action)
        self.toolbar.addAction(pair_action)
        self.toolbar.addWidget(spacer_left)
        self.toolbar.addWidget(self.combo_box)
        self.toolbar.addWidget(spacer_right)
        self.toolbar.addAction(export_action)
        self.toolbar.addAction(preferences_action)

        self.status_bar = self.statusBar()
        self.status_bar_label = QLabel('Initializing...')
        self.status_bar.addPermanentWidget(self.status_bar_label)

        self.preferences_widget = PreferencesWidget()
        self.preferences_widget.accepted.connect(self.show_selected_grid_view)

        self.active_pair_widgets = []
        self.active_invite_receivers = []

    def populate(self, gateways):
        for gateway in gateways:
            if gateway not in self.gateways:
                self.gateways.append(gateway)
        self.combo_box.populate(self.gateways)
        self.central_widget.populate(self.gateways)
        self.central_widget.addWidget(self.preferences_widget)
        self.gui.systray.menu.populate()

    def current_view(self):
        return self.central_widget.currentWidget().layout().itemAt(0).widget()

    def select_folder(self):
        try:
            view = self.current_view()
        except AttributeError:
            return
        view.select_folder()

    def set_current_grid_status(self):
        if self.central_widget.currentWidget() == self.preferences_widget:
            return
        self.status_bar_label.setText(
            self.current_view().model().grid_status)
        self.gui.systray.update()

    def show_setup_form(self):
        if self.setup_form:
            self.setup_form.close()
        self.setup_form = SetupForm(self.gui, self.gateways)
        self.setup_form.show()
        self.setup_form.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.show_setup_form()
        else:
            self.central_widget.setCurrentIndex(index)
            self.status_bar.show()
            self.set_current_grid_status()

    def show_selected_grid_view(self):
        for i in range(self.central_widget.count()):
            widget = self.central_widget.widget(i)
            try:
                gateway = widget.layout().itemAt(0).widget().gateway
            except AttributeError:
                continue
            if gateway == self.combo_box.currentData():
                self.central_widget.setCurrentIndex(i)
                self.status_bar.show()
                self.set_current_grid_status()
                return
        self.combo_box.setCurrentIndex(0)  # Fallback to 0 if none selected
        self.on_grid_selected(0)

    def show_error_msg(self, title, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))
        msg.exec_()

    def show_info_msg(self, title, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(str(title))
        msg.setText(str(text))
        msg.exec_()

    def confirm_export(self, path):
        if os.path.isfile(path):  # TODO: Confirm contents?
            self.show_info_msg(
                "Export successful",
                "Recovery Key successfully exported to {}".format(path))
        else:
            self.show_error_msg(
                "Error exporting Recovery Key",
                "Destination file not found after export: {}".format(path))

    def on_encryption_succeeded(self, ciphertext):
        self.crypter_thread.quit()
        if self.export_dest:
            with open(self.export_dest, 'wb') as f:
                f.write(ciphertext)
            self.confirm_export(self.export_dest)
            self.export_dest = None
        else:
            self.export_data = ciphertext
        self.crypter_thread.wait()

    def on_encryption_failed(self, message):
        self.crypter_thread.quit()
        self.show_error_msg(
            "Error encrypting data",
            "Encryption failed: " + message)
        self.crypter_thread.wait()

    def export_encrypted_recovery(self, gateway, password):
        settings = gateway.get_settings(include_rootcap=True)
        data = json.dumps(settings)
        self.progress = QProgressDialog("Encrypting...", None, 0, 100)
        self.progress.show()
        self.animation = QPropertyAnimation(self.progress, b'value')
        self.animation.setDuration(4500)  # XXX
        self.animation.setStartValue(0)
        self.animation.setEndValue(99)
        self.animation.start()
        self.crypter = Crypter(data.encode(), password.encode())
        self.crypter_thread = QThread()
        self.crypter.moveToThread(self.crypter_thread)
        self.crypter.succeeded.connect(self.animation.stop)
        self.crypter.succeeded.connect(self.progress.close)
        self.crypter.succeeded.connect(self.on_encryption_succeeded)
        self.crypter.failed.connect(self.animation.stop)
        self.crypter.failed.connect(self.progress.close)
        self.crypter.failed.connect(self.on_encryption_failed)
        self.crypter_thread.started.connect(self.crypter.encrypt)
        self.crypter_thread.start()
        dest, _ = QFileDialog.getSaveFileName(
            self, "Select a destination", os.path.join(
                os.path.expanduser('~'),
                gateway.name + ' Recovery Key.json.encrypted'))
        if not dest:
            return
        if self.export_data:
            with open(dest, 'wb') as f:
                f.write(self.export_data)
            self.confirm_export(dest)
            self.export_data = None
        else:
            self.export_dest = dest

    def export_plaintext_recovery(self, gateway):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Select a destination", os.path.join(
                os.path.expanduser('~'), gateway.name + ' Recovery Key.json'))
        if not dest:
            return
        try:
            gateway.export(dest, include_rootcap=True)
        except Exception as e:  # pylint: disable=broad-except
            self.show_error_msg("Error exporting Recovery Key", str(e))
            return
        self.confirm_export(dest)

    def export_recovery_key(self, gateway=None):
        self.show_selected_grid_view()
        if not gateway:
            gateway = self.current_view().gateway
        password, ok = PasswordDialog.get_password(
            self, "Encryption passphrase (optional):")
        if ok and password:
            self.export_encrypted_recovery(gateway, password)
        elif ok:
            self.export_plaintext_recovery(gateway)

    def toggle_preferences_widget(self):
        if self.central_widget.currentWidget() == self.preferences_widget:
            self.show_selected_grid_view()
        else:
            self.status_bar.hide()
            for i in range(self.central_widget.count()):
                if self.central_widget.widget(i) == self.preferences_widget:
                    self.central_widget.setCurrentIndex(i)

    def on_invite_received(self, _):
        for view in self.central_widget.views:
            view.model().monitor.scan_rootcap('star.png')

    def open_invite_receiver(self):
        invite_receiver = InviteReceiver(self.gateways)
        invite_receiver.done.connect(self.on_invite_received)
        invite_receiver.closed.connect(self.active_invite_receivers.remove)
        invite_receiver.show()
        self.active_invite_receivers.append(invite_receiver)

    def open_pair_widget(self):
        gateway = self.combo_box.currentData()
        if gateway:
            pair_widget = ShareWidget(gateway, self.gui)
            pair_widget.closed.connect(self.active_pair_widgets.remove)
            pair_widget.show()
            self.active_pair_widgets.append(pair_widget)

    def confirm_quit(self):
        reply = QMessageBox.question(
            self, "Exit {}?".format(APP_NAME),
            "Are you sure you wish to quit? If you quit, {} will stop "
            "synchronizing your folders until you run it again.".format(
                APP_NAME),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            reactor.stop()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            view = self.current_view()
            selected = view.selectedIndexes()
            if selected:
                for index in selected:
                    view.selectionModel().select(
                        index, QItemSelectionModel.Deselect)
            elif self.gui.systray.isSystemTrayAvailable():
                self.hide()

    def closeEvent(self, event):
        if self.gui.systray.isSystemTrayAvailable():
            event.accept()
        else:
            event.ignore()
            self.confirm_quit()
