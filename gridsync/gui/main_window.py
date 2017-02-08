# -*- coding: utf-8 -*-

import os

from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileIconProvider, QGridLayout, QHeaderView, QLabel,
    QMainWindow, QSizePolicy, QStackedWidget, QTreeView, QWidget)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QStandardItem, QStandardItemModel)
from PyQt5.QtCore import QFileInfo, QSize, Qt, QVariant

from gridsync import resource, settings
from gridsync.tahoe import get_nodedirs


class ComboBox(QComboBox):
    def __init__(self):
        super(self.__class__, self).__init__()

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


class Model(QStandardItemModel):
    def __init__(self, nodedir):
        super(self.__class__, self).__init__(0, 4)
        self.nodedir = nodedir
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Size"))
        self.setHeaderData(3, Qt.Horizontal, QVariant("Action"))

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
        magic_folders_dir = os.path.join(self.nodedir, 'magic-folders')
        if os.path.isdir(magic_folders_dir):
            for magic_folder in get_nodedirs(magic_folders_dir):
                self.add_folder(magic_folder)


class View(QTreeView):
    def __init__(self, nodedir):
        super(self.__class__, self).__init__()
        self.nodedir = nodedir
        self.model = Model(self.nodedir)
        self.setModel(self.model)
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 50)
        self.setColumnWidth(3, 100)
        #self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        font = QFont()
        font.setPointSize(12)
        #self.header().setFont(font)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.header().setSectionResizeMode(3, QHeaderView.Stretch)


class CentralWidget(QStackedWidget):
    def __init__(self):
        super(self.__class__, self).__init__()

    def clear(self):
        for _ in range(self.count()):
            self.removeWidget(self.currentWidget())

    def add_view_widget(self, nodedir):
        view = View(nodedir)
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.addWidget(view)
        self.addWidget(widget)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            self.add_view_widget(gateway.nodedir)

    def add_new_folder(self, path):
        current_model = self.currentWidget().layout().itemAt(0).widget().model
        current_model.add_folder(path)
        # TODO: Create magic-folder


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
        self.status_bar.addPermanentWidget(
            QLabel('Connection status goes here :)'))

        self.setAcceptDrops(True)

    def populate(self, gateways):
        self.combo_box.populate(gateways)
        self.central_widget.populate(gateways)

    def on_grid_selected(self, index):
        self.central_widget.setCurrentIndex(index)

    def dragEnterEvent(self, event):  # pylint: disable=no-self-use
        if event.mimeData().hasUrls:
            event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
            for url in event.mimeData().urls():
                self.central_widget.add_new_folder(url.toLocalFile())

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()
