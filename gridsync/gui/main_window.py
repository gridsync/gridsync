# -*- coding: utf-8 -*-

import logging
import os
from collections import defaultdict

from humanize import naturalsize
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QComboBox, QFileIconProvider, QGridLayout,
    QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox, QSizePolicy,
    QStackedWidget, QTreeView, QWidget)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QPixmap, QStandardItem, QStandardItemModel)
from PyQt5.QtCore import QEvent, QFileInfo, QSize, Qt, QVariant
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

from gridsync import resource, APP_NAME
from gridsync.desktop import open_folder
from gridsync.tahoe import get_nodedirs
from gridsync.util import humanized_list


class ComboBox(QComboBox):
    def __init__(self):
        super(ComboBox, self).__init__()
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            basename = os.path.basename(os.path.normpath(gateway.nodedir))
            iconpath = os.path.join(gateway.nodedir, 'icon')
            if not os.path.isfile(iconpath):
                iconpath = resource('tahoe-lafs.png')
            self.addItem(QIcon(iconpath), basename)
        self.insertSeparator(self.count())
        self.addItem(" Add new...")
        #self.model().item(self.count() - 1).setEnabled(False)


class Monitor(object):
    def __init__(self, model):
        self.model = model
        self.gateway = self.model.gateway
        self.gui = self.model.gui
        self.grid_status = ''
        self.status = defaultdict(dict)
        self.timer = LoopingCall(self.check_status)

    def add_updated_file(self, magic_folder, path):
        if 'updated_files' not in self.status[magic_folder]:
            self.status[magic_folder]['updated_files'] = []
        if path in self.status[magic_folder]['updated_files']:
            return
        elif path.endswith('/') or path.endswith('~') or path.isdigit():
            return
        else:
            self.status[magic_folder]['updated_files'].append(path)
            logging.debug("Added %s to updated_files list", path)

    def notify_updated_files(self, magic_folder):
        if 'updated_files' in self.status[magic_folder]:
            title = magic_folder.name + " updated and encrypted"
            message = "Updated " + humanized_list(
                self.status[magic_folder]['updated_files'])
            self.gui.show_message(title, message)
            self.status[magic_folder]['updated_files'] = []
            logging.debug("Cleared updated_files list")

    def get_state_from_status(self, status):
        state = 0
        if status:
            for task in status:
                if task['status'] == 'queued' or task['status'] == 'started':
                    if not task['path'].endswith('/'):
                        state = 1  # "Syncing"
            if not state:
                state = 2  # "Up to date"
        return state

    @inlineCallbacks
    def check_magic_folder_status(self, magic_folder):
        status = yield magic_folder.get_magic_folder_status()
        state = self.get_state_from_status(status)
        prev = self.status[magic_folder]
        if status and prev:
            if prev['status'] and status != prev['status']:
                for item in status:
                    if item not in prev['status']:
                        self.add_updated_file(magic_folder, item['path'])
                size = yield magic_folder.get_magic_folder_size()
                self.model.set_size(magic_folder.name, size)
            if state == 2 and prev['state'] != 2:
                self.notify_updated_files(magic_folder)
                size = yield magic_folder.get_magic_folder_size()
                self.model.set_size(magic_folder.name, size)
        self.status[magic_folder]['status'] = status
        self.status[magic_folder]['state'] = state
        self.model.set_status(magic_folder.name, state)

    @inlineCallbacks
    def check_grid_status(self):
        num_connected = yield self.gateway.get_connected_servers()
        if not num_connected:
            grid_status = "Connecting..."
        elif num_connected == 1:
            grid_status = "Connected to {} storage node".format(num_connected)
        else:
            grid_status = "Connected to {} storage nodes".format(num_connected)
        if num_connected and grid_status != self.grid_status:
            self.gui.show_message(self.gateway.name, grid_status)
        self.grid_status = grid_status

    def check_status(self):
        self.check_grid_status()
        for magic_folder in self.gateway.magic_folders:
            self.check_magic_folder_status(magic_folder)

    def start(self, interval=2):
        self.timer.start(interval, now=True)


class Model(QStandardItemModel):
    def __init__(self, view):
        super(Model, self).__init__(0, 3)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = Monitor(self)
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Size"))
        #self.setHeaderData(3, Qt.Horizontal, QVariant("Action"))

        self.icon_up_to_date = QIcon(resource('checkmark.png'))
        self.icon_syncing = QIcon(resource('sync.png'))

    def data(self, index, role):
        value = super(Model, self).data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path):
        folder_icon = QFileIconProvider().icon(QFileInfo(path))
        folder_basename = os.path.basename(os.path.normpath(path))
        name = QStandardItem(folder_icon, folder_basename)
        status = QStandardItem()
        size = QStandardItem()
        #action = QStandardItem(QIcon(resource('share.png')), '')
        self.appendRow([name, status, size])
        self.view.hide_drop_label()

    def populate(self):
        for magic_folder in get_nodedirs(self.gateway.magic_folders_dir):
            self.add_folder(magic_folder)
        self.monitor.start()

    def get_row_from_name(self, name):
        for row in range(self.rowCount()):
            if name == self.item(row).text():
                return row

    def set_status(self, name, status):
        if not status:
            icon = QIcon()
            text = None
        elif status == 1:
            icon = self.icon_syncing
            text = "Syncing"
        else:
            icon = self.icon_up_to_date
            text = "Up to date"
        self.setItem(
            self.get_row_from_name(name), 1, QStandardItem(icon, text))

    def set_size(self, name, size):
        self.setItem(
            self.get_row_from_name(name), 2, QStandardItem(naturalsize(size)))


class View(QTreeView):
    def __init__(self, gui, gateway):
        super(View, self).__init__()
        self.gui = gui
        self.gateway = gateway
        self.setModel(Model(self))
        self.setAcceptDrops(True)
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 75)
        #self.setColumnWidth(3, 75)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        #font = QFont()
        #font.setPointSize(12)
        #self.header().setFont(font)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(3, QHeaderView.Stretch)

        self.drop_text = QLabel(self)
        self.drop_text.setText('<i>Drop folders here</i>')
        drop_text_font = QFont()
        drop_text_font.setPointSize(14)
        self.drop_text.setFont(drop_text_font)
        self.drop_text.setStyleSheet('color: grey')
        self.drop_text.setAlignment(Qt.AlignCenter)
        self.drop_text.setAcceptDrops(True)
        self.drop_text.installEventFilter(self)
        self.drop_text.setSizePolicy(QSizePolicy.Expanding, 0)

        self.drop_pixmap = QLabel(self)
        self.drop_pixmap.setPixmap(QPixmap(resource('drop_zone.png')))
        self.drop_pixmap.setScaledContents(True)
        self.drop_pixmap.setAcceptDrops(True)
        self.drop_pixmap.installEventFilter(self)

        layout = QGridLayout(self)
        layout.addWidget(self.drop_pixmap, 1, 1, 6, 3)
        layout.addWidget(self.drop_text, 5, 2)

        self.doubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.model().populate()

    def show_drop_label(self):
        self.setHeaderHidden(True)
        self.drop_text.show()
        self.drop_pixmap.show()

    def hide_drop_label(self):
        self.setHeaderHidden(False)
        self.drop_text.hide()
        self.drop_pixmap.hide()

    def on_double_click(self, index):
        item = self.model().itemFromIndex(index)
        if item.column() == 0:
            for mf in self.gateway.magic_folders:
                if mf.name == item.text():
                    localdir = mf.config_get('magic_folder', 'local.directory')
                    open_folder(localdir)

    def confirm_remove(self, folder):
        reply = QMessageBox.question(
            self, "Remove '{}'?".format(folder),
            "Are you sure you wish to remove the '{}' folder? If you do, it "
            "will remain on your computer, however, {} will no longer "
            "synchronize its contents with {}.".format(
                folder, APP_NAME, self.gateway.name),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.gateway.remove_magic_folder(folder)
            self.model().removeRow(self.model().get_row_from_name(folder))
            if not self.gateway.magic_folders:
                self.show_drop_label()

    def on_right_click(self, position):
        item = self.model().itemFromIndex(self.indexAt(position))
        if item:
            folder = self.model().item(item.row(), 0).text()
            menu = QMenu()
            remove_action = QAction(
                QIcon(resource('close.png')), "Remove", menu)
            remove_action.triggered.connect(
                lambda: self.confirm_remove(folder))
            menu.addAction(remove_action)
            menu.exec_(self.viewport().mapToGlobal(position))

    def add_new_folder(self, path):
        self.hide_drop_label()
        self.model().add_folder(path)
        self.gateway.create_magic_folder(path)

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

    def eventFilter(self, obj, event):
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

    def clear(self):
        for _ in range(self.count()):
            self.removeWidget(self.currentWidget())

    def add_view_widget(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.addWidget(view)
        self.addWidget(widget)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            self.add_view_widget(gateway)


class MainWindow(QMainWindow):
    def __init__(self, gui):
        super(MainWindow, self).__init__()
        self.gui = gui
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(500, 300))

        self.combo_box = ComboBox()
        self.combo_box.activated[int].connect(self.on_grid_selected)

        self.central_widget = CentralWidget(self.gui)
        self.setCentralWidget(self.central_widget)

        invite_action = QAction(
            QIcon(resource('mail-envelope-open')), 'Enter Invite Code', self)
        invite_action.setStatusTip('Enter Invite Code')
        invite_action.setShortcut(QKeySequence.Open)
        invite_action.triggered.connect(self.gui.show_invite_form)

        preferences_action = QAction(
            QIcon(resource('preferences.png')), 'Preferences', self)
        preferences_action.setStatusTip('Preferences')
        preferences_action.setShortcut(QKeySequence.Preferences)
        #preferences_action.triggered.connect(self.close)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        self.toolbar = self.addToolBar('')
        #self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        #self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.setMovable(False)
        #self.toolbar.addAction(invite_action)
        self.toolbar.addWidget(spacer_left)
        self.toolbar.addWidget(self.combo_box)
        self.toolbar.addWidget(spacer_right)
        #self.toolbar.addAction(preferences_action)

        self.status_bar = self.statusBar()
        self.status_bar_label = QLabel('Initializing...')
        self.status_bar.addPermanentWidget(self.status_bar_label)

        self.grid_status_updater = LoopingCall(self.set_current_grid_status)

    def populate(self, gateways):
        self.combo_box.populate(gateways)
        self.central_widget.populate(gateways)
        self.grid_status_updater.start(2, now=True)

    def current_widget(self):
        return self.central_widget.currentWidget().layout().itemAt(0).widget()

    def get_current_grid_status(self):
        return self.current_widget().model().monitor.grid_status

    def set_current_grid_status(self):
        self.status_bar_label.setText(self.get_current_grid_status())

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.gui.show_invite_form()
        else:
            self.central_widget.setCurrentIndex(index)
            self.set_current_grid_status()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()

    def closeEvent(self, event):  # pylint: disable=all
        reply = QMessageBox.question(
            self, "Exit {}?".format(APP_NAME),
            "Are you sure you wish to quit? If you quit, {} will stop "
            "synchronizing your folders until you run it again.".format(
                APP_NAME),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
            reactor.stop()
        else:
            event.ignore()
