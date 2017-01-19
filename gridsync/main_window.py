# -*- coding: utf-8 -*-

from __future__ import print_function

import os

from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileIconProvider, QHeaderView, QLabel, QMainWindow,
    QSizePolicy, QTreeView, QVBoxLayout, QWidget)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QStandardItem, QStandardItemModel)
from PyQt5.QtCore import QFileInfo, QSize, Qt, QVariant

from gridsync import settings
from gridsync.config import Config
from gridsync.resource import resource


class ComboBox(QComboBox):
    # XXX: Update/merge with GridSelector widget
    def __init__(self):
        super(self.__class__, self).__init__()
        providers = Config(resource('storage_providers.txt')).load()
        for provider in sorted(providers):
            self.addItem(
                QIcon(resource(providers[provider]['icon'])), provider)
        self.insertSeparator(self.count())
        self.addItem(" Add new...")
        self.model().item(self.count() - 1).setEnabled(False)


class Folder(QStandardItem):
    def __init__(self, path):
        super(self.__class__, self).__init__()
        self.setIcon(QFileIconProvider().icon(QFileInfo(path)))
        self.setText(os.path.basename(os.path.normpath(path)))


class Model(QStandardItemModel):
    def __init__(self):
        super(self.__class__, self).__init__(0, 4)
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Size"))
        self.setHeaderData(3, Qt.Horizontal, QVariant("Action"))

    def data(self, index, role):
        value = super(self.__class__, self).data(index, role)
        if role == Qt.SizeHintRole:
            return QSize(0, 30)
        return value

    def add_folder(self, path):
        name = Folder(path)
        status = QStandardItem()
        size = QStandardItem()
        action = QStandardItem(QIcon(), '')
        self.appendRow([name, status, size, action])


class MainWindow(QMainWindow):
    def __init__(self, parent):
        super(self.__class__, self).__init__()
        self.parent = parent
        self.setWindowTitle(settings['application']['name'])
        self.setMinimumSize(QSize(500, 300))

        self.combo_box = ComboBox()
        self.model = Model()

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setColumnWidth(0, 100)
        self.view.setColumnWidth(1, 100)
        self.view.setColumnWidth(2, 50)
        self.view.setColumnWidth(3, 100)
        #self.view.setHeaderHidden(True)
        #self.view.setRootIsDecorated(False)
        self.view.setSortingEnabled(True)
        #self.view.header().setDefaultAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        #self.view.header().setFont(font)
        self.view.header().setStretchLastSection(False)
        self.view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.view.header().setSectionResizeMode(3, QHeaderView.Stretch)

        self.central_widget = QWidget()
        self.vbox = QVBoxLayout(self.central_widget)
        self.vbox.addWidget(self.view)
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

    def dragEnterEvent(self, event):  # pylint: disable=no-self-use
        if event.mimeData().hasUrls:
            event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
            for url in event.mimeData().urls():
                self.model.add_folder(url.toLocalFile())

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.hide()
