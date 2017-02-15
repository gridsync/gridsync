# -*- coding: utf-8 -*-

import logging
import os

from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QComboBox, QFileIconProvider, QGridLayout,
    QHeaderView, QLabel, QMainWindow, QSizePolicy, QStackedWidget, QTreeView,
    QWidget)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QStandardItem, QStandardItemModel)
from PyQt5.QtCore import QFileInfo, QSize, Qt, QVariant
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

from gridsync import resource, settings
from gridsync.desktop import open_folder
from gridsync.tahoe import get_nodedirs


class ComboBox(QComboBox):
    def __init__(self):
        super(self.__class__, self).__init__()
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
        self.model().item(self.count() - 1).setEnabled(False)


class Monitor(object):
    def __init__(self, parent, gateway):
        self.parent = parent
        self.gateway = gateway
        self.status = ''
        self.timer = LoopingCall(self.update_status)
        self.magic_folders_status = {}

    @inlineCallbacks
    def get_magic_folder_state(self, magic_folder):
        status = yield magic_folder.get_magic_folder_status()
        state = 0
        if status:
            for task in status:
                if task['status'] == 'queued' or task['status'] == 'started':
                    state = 1
        returnValue(state)

    @inlineCallbacks
    def update_status(self):
        num_connected = yield self.gateway.get_connected_servers()
        if not num_connected:
            self.status = "Connecting..."
        elif num_connected == 1:
            self.status = "Connected to {} storage node".format(num_connected)
        else:
            self.status = "Connected to {} storage nodes".format(num_connected)
        if self.gateway.magic_folders:
            for magic_folder in self.gateway.magic_folders:
                state = yield self.get_magic_folder_state(magic_folder)
                self.magic_folders_status[magic_folder.name] = state
            self.parent.update(self.magic_folders_status)

    def start(self, interval=2):
        self.timer.start(interval, now=True)


class Model(QStandardItemModel):
    def __init__(self, gateway):
        super(self.__class__, self).__init__(0, 4)
        self.gateway = gateway
        self.monitor = Monitor(self, gateway)
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Size"))
        self.setHeaderData(3, Qt.Horizontal, QVariant("Action"))

        self.icon_up_to_date = QIcon(resource('checkmark.png'))
        self.icon_syncing = QIcon(resource('sync.png'))

        self.populate()

    def data(self, index, role):
        value = super(self.__class__, self).data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path):
        folder_icon = QFileIconProvider().icon(QFileInfo(path))
        folder_basename = os.path.basename(os.path.normpath(path))
        name = QStandardItem(folder_icon, folder_basename)
        status = QStandardItem()
        size = QStandardItem()
        action = QStandardItem(QIcon(), '')
        self.appendRow([name, status, size, action])

    def populate(self):
        magic_folders_dir = os.path.join(self.gateway.nodedir, 'magic-folders')
        if os.path.isdir(magic_folders_dir):
            for magic_folder in get_nodedirs(magic_folders_dir):
                self.add_folder(magic_folder)
        self.monitor.start()

    def update(self, data):
        for folder, state in data.items():
            for row in range(self.rowCount()):
                if folder == self.item(row, 0).text():
                    if state == 0:
                        icon = self.icon_up_to_date
                        text = "Up to date"
                    else:
                        icon = self.icon_syncing
                        text = "Syncing"
                    self.setItem(row, 1, QStandardItem(icon, text))


class View(QTreeView):
    def __init__(self, gateway):
        super(self.__class__, self).__init__()
        self.gateway = gateway
        self.setModel(Model(self.gateway))
        self.setAcceptDrops(True)
        self.setColumnWidth(0, 150)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 75)
        self.setColumnWidth(3, 75)
        #self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        font = QFont()
        font.setPointSize(12)
        #self.header().setFont(font)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        #self.header().setSectionResizeMode(3, QHeaderView.Stretch)

        self.doubleClicked.connect(self.on_double_click)

    def on_double_click(self, index):
        item = self.model().itemFromIndex(index)
        if item.column() == 0:
            for mf in self.gateway.magic_folders:
                if mf.name == item.text():
                    localdir = mf.config_get('magic_folder', 'local.directory')
                    open_folder(localdir)

    def add_new_folder(self, path):
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
                self.add_new_folder(url.toLocalFile())


class CentralWidget(QStackedWidget):
    def __init__(self):
        super(self.__class__, self).__init__()

    def clear(self):
        for _ in range(self.count()):
            self.removeWidget(self.currentWidget())

    def add_view_widget(self, gateway):
        view = View(gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.addWidget(view)
        self.addWidget(widget)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            self.add_view_widget(gateway)

class MainWindow(QMainWindow):
    def __init__(self, parent):
        super(self.__class__, self).__init__()
        self.parent = parent
        self.setWindowTitle(settings['application']['name'])
        self.setMinimumSize(QSize(500, 300))

        self.combo_box = ComboBox()
        self.combo_box.activated[int].connect(self.on_grid_selected)

        self.central_widget = CentralWidget()
        self.setCentralWidget(self.central_widget)

        invite_action = QAction(
            QIcon(resource('mail-envelope-open')), 'Enter Invite Code', self)
        invite_action.setStatusTip('Enter Invite Code')
        invite_action.setShortcut(QKeySequence.Open)
        invite_action.triggered.connect(self.parent.show_invite_form)

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
        self.toolbar.addAction(invite_action)
        self.toolbar.addWidget(spacer_left)
        self.toolbar.addWidget(self.combo_box)
        self.toolbar.addWidget(spacer_right)
        self.toolbar.addAction(preferences_action)

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
        return self.current_widget().model().monitor.status

    def set_current_grid_status(self):
        self.status_bar_label.setText(self.get_current_grid_status())

    def on_grid_selected(self, index):
        self.central_widget.setCurrentIndex(index)
        self.set_current_grid_status()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()

    def closeEvent(self, event):  # pylint: disable=all
        reactor.stop()
