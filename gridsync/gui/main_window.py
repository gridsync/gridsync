# -*- coding: utf-8 -*-

from __future__ import print_function

import logging as log
import os

from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileIconProvider, QGridLayout, QHeaderView, QLabel,
    QMainWindow, QSizePolicy, QStackedWidget, QTreeView, QWidget)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QStandardItem, QStandardItemModel)
from PyQt5.QtCore import QFileInfo, QSize, Qt, QVariant

from gridsync import config_dir, resource, settings
from gridsync.tahoe import get_nodedirs


class ComboBox(QComboBox):
    def __init__(self, nodedirs=None):
        super(self.__class__, self).__init__()
        self.populate(nodedirs)

    def populate(self, nodedirs):
        if not nodedirs:
            nodedirs = get_nodedirs(config_dir)
        self.clear()
        for nodedir in sorted(nodedirs):
            basename = os.path.basename(os.path.normpath(nodedir))
            iconpath = os.path.join(nodedir, 'icon')
            if not os.path.isfile(iconpath):
                iconpath = resource('tahoe-lafs.png')
            self.addItem(QIcon(iconpath), basename)
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


class View(QTreeView):
    def __init__(self, model):
        super(self.__class__, self).__init__()
        self.model = model
        self.setModel(self.model)
        self.setColumnWidth(0, 100)
        self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 50)
        self.setColumnWidth(3, 100)
        #self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        #self.header().setDefaultAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        #self.header().setFont(font)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.header().setSectionResizeMode(3, QHeaderView.Stretch)


class CentralWidget(QStackedWidget):
    def __init__(self, view):
        super(self.__class__, self).__init__()
        self.view = view

        self.view_widget = QWidget()
        layout = QGridLayout(self.view_widget)
        layout.addWidget(self.view)

        self.addWidget(self.view_widget)
        self.setCurrentIndex(0)


class MainWindow(QMainWindow):
    def __init__(self, parent, nodedirs=None):
        super(self.__class__, self).__init__()
        self.parent = parent
        self.nodedirs = nodedirs
        self.setWindowTitle(settings['application']['name'])
        self.setMinimumSize(QSize(500, 300))

        self.combo_box = ComboBox(self.nodedirs)
        self.combo_box.activated[str].connect(self.on_grid_selected)

        self.model = Model()
        self.view = View(self.model)

        #self.central_widget = QWidget()
        #self.vbox = QVBoxLayout(self.central_widget)
        #self.vbox.addWidget(self.view)
        self.central_widget = CentralWidget(self.view)
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

    def on_grid_selected(self, name):  # pylint: disable=no-self-use
        log.debug("Selected: %s", name)

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
