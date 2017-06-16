# -*- coding: utf-8 -*-

import logging
import os

from humanize import naturalsize
from PyQt5.QtCore import (
    pyqtSignal, QEvent, QFileInfo, QPoint, QSize, Qt, QVariant)
from PyQt5.QtGui import (
    QFont, QIcon, QKeySequence, QMovie, QPixmap, QStandardItem,
    QStandardItemModel)
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QComboBox, QFileDialog, QFileIconProvider,
    QGridLayout, QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox,
    QShortcut, QSizePolicy, QStackedWidget, QStyledItemDelegate, QTreeView,
    QWidget)
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from gridsync import resource, APP_NAME
from gridsync.desktop import open_folder
from gridsync.gui.widgets import CompositePixmap
from gridsync.monitor import Monitor
from gridsync.tahoe import get_nodedirs


class ComboBox(QComboBox):
    def __init__(self):
        super(ComboBox, self).__init__()
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)

    def populate(self, gateways):
        self.clear()
        for gateway in gateways:
            basename = os.path.basename(os.path.normpath(gateway.nodedir))
            icon = QIcon(os.path.join(gateway.nodedir, 'icon'))
            if not icon.availableSizes():
                icon = QIcon(resource('tahoe-lafs.png'))
            self.addItem(icon, basename)
        self.insertSeparator(self.count())
        self.addItem(" Add new...")
        #self.model().item(self.count() - 1).setEnabled(False)


class Model(QStandardItemModel):
    def __init__(self, view):
        super(Model, self).__init__(0, 4)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = Monitor(self)
        self.status_dict = {}
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Last sync"))
        self.setHeaderData(3, Qt.Horizontal, QVariant("Size"))
        #self.setHeaderData(4, Qt.Horizontal, QVariant("Action"))

        self.icon_blank = QIcon()
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
        #name = QStandardItem(folder_icon, folder_basename)
        folder_pixmap = folder_icon.pixmap(256, 256)
        lock_pixmap = resource('lock-closed-green.svg')
        composite_pixmap = CompositePixmap(folder_pixmap, lock_pixmap)
        name = QStandardItem(QIcon(composite_pixmap), folder_basename)
        status = QStandardItem(QIcon(), "Initializing...")
        size = QStandardItem()
        #action = QStandardItem(QIcon(resource('share.png')), '')
        self.appendRow([name, status, size])
        self.view.hide_drop_label()
        self.set_status(folder_basename, 0)

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
            icon = self.icon_blank
            text = "Initializing..."
        elif status == 1:
            icon = self.icon_syncing
            text = "Syncing"
        else:
            icon = self.icon_up_to_date
            text = "Up to date"
        item = QStandardItem(icon, text)
        item.setData(status, Qt.UserRole)
        self.setItem(self.get_row_from_name(name), 1, item)
        self.status_dict[name] = status

    def set_last_sync(self, name, text):
        self.setItem(self.get_row_from_name(name), 2, QStandardItem(text))

    def set_size(self, name, size):
        self.setItem(
            self.get_row_from_name(name), 3, QStandardItem(naturalsize(size)))


class Delegate(QStyledItemDelegate):

    updated = pyqtSignal()

    def __init__(self, parent=None):
        super(Delegate, self).__init__(parent=None)
        self.parent = parent
        self.movie = QMovie(resource('waiting.gif'))
        self.movie.setCacheMode(True)
        self.movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self):
        if 0 in self.parent.model().status_dict.values():
            self.updated.emit()

    def paint(self, painter, option, index):
        column = index.column()
        if column == 1:
            status = index.data(Qt.UserRole)
            if not status:  # "Initializing..."
                point = option.rect.topLeft()
                pixmap = self.movie.currentPixmap().scaled(20, 20)
                painter.drawPixmap(QPoint(point.x(), point.y() + 5), pixmap)
                option.rect = option.rect.translated(pixmap.width(), 0)
        super(Delegate, self).paint(painter, option, index)


class View(QTreeView):
    def __init__(self, gui, gateway):
        super(View, self).__init__()
        self.gui = gui
        self.gateway = gateway
        self.setModel(Model(self))
        delegate = Delegate(self)
        delegate.updated.connect(self.viewport().update)
        delegate.movie.start()
        self.setItemDelegate(delegate)

        self.setAcceptDrops(True)
        #self.setColumnWidth(0, 150)
        #self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 75)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setHeaderHidden(True)
        #self.setRootIsDecorated(False)
        self.setSortingEnabled(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
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
                QIcon(resource('close.png')), "Remove {}".format(folder), menu)
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
        self.gateways = []
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(500, 300))

        self.shortcut_new = QShortcut(QKeySequence.New, self)
        self.shortcut_new.activated.connect(self.gui.show_setup_form)

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

        #invite_action = QAction(
        #    QIcon(resource('mail-envelope-open')), 'Enter Invite Code', self)
        #invite_action.setStatusTip('Enter Invite Code')
        #invite_action.setShortcut(QKeySequence.Open)
        #invite_action.triggered.connect(self.gui.show_invite_form)

        #preferences_action = QAction(
        #    QIcon(resource('preferences.png')), 'Preferences', self)
        #preferences_action.setStatusTip('Preferences')
        #preferences_action.setShortcut(QKeySequence.Preferences)

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
        for gateway in gateways:
            if gateway not in self.gateways:
                self.gateways.append(gateway)
        self.combo_box.populate(self.gateways)
        self.central_widget.populate(self.gateways)
        try:
            self.grid_status_updater.start(2, now=True)
        except AssertionError:  # Tried to start an already running LoopingCall
            pass

    def current_view(self):
        return self.central_widget.currentWidget().layout().itemAt(0).widget()

    def select_folder(self):
        try:
            view = self.current_view()
        except AttributeError:
            return
        dialog = QFileDialog(self, "Please select a folder")
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly)
        if dialog.exec_():
            for folder in dialog.selectedFiles():
                view.add_new_folder(folder)

    def get_current_grid_status(self):
        return self.current_view().model().monitor.grid_status

    def set_current_grid_status(self):
        self.status_bar_label.setText(self.get_current_grid_status())
        self.gui.systray.update()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.gui.show_setup_form()
        else:
            self.central_widget.setCurrentIndex(index)
            self.set_current_grid_status()

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
        if key == Qt.Key_Escape and self.gui.systray.isSystemTrayAvailable():
            self.hide()

    def closeEvent(self, event):
        if self.gui.systray.isSystemTrayAvailable():
            event.accept()
        else:
            event.ignore()
            self.confirm_quit()
