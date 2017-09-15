# -*- coding: utf-8 -*-

import logging
import os
import shutil

from humanize import naturalsize
from PyQt5.QtCore import QEvent, QFileInfo, QPoint, QSize, Qt, QVariant
from PyQt5.QtGui import (
    QColor, QFont, QIcon, QKeySequence, QMovie, QPixmap, QStandardItem,
    QStandardItemModel)
from PyQt5.QtWidgets import (
    QAbstractItemView, QAction, QComboBox, QFileDialog, QFileIconProvider,
    QGridLayout, QHeaderView, QLabel, QMainWindow, QMenu, QMessageBox,
    QPushButton, QShortcut, QSizePolicy, QSpacerItem, QStackedWidget,
    QStyledItemDelegate, QToolBar, QTreeView, QWidget)
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

from gridsync import resource, APP_NAME, config_dir
from gridsync.desktop import open_folder
from gridsync.gui.widgets import (
    CompositePixmap, InviteReceiver, PreferencesWidget, ShareWidget)
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
            self.addItem(icon, basename, gateway)
        self.insertSeparator(self.count())
        self.addItem(" Add new...")
        #self.model().item(self.count() - 1).setEnabled(False)


class ActionBar(QToolBar):
    def __init__(self, parent, basename):
        super(ActionBar, self).__init__()
        self.parent = parent
        self.basename = basename
        self.gateway = self.parent.gateway
        self.gui = self.parent.gui
        self.share_widget = None
        self.setIconSize(QSize(16, 16))

        self.share_action = QAction(
            QIcon(resource('share.png')), 'Share...', self)
        self.share_action.setStatusTip('Share...')
        self.share_action.triggered.connect(self.open_share_widget)

        self.download_action = QAction(
            QIcon(resource('download.png')), 'Download...', self)
        self.download_action.setStatusTip('Download...')

    def open_share_widget(self):
        self.share_widget = ShareWidget(self.gateway, self.gui, self.basename)
        self.share_widget.show()

    def add_share_button(self):
        self.addAction(self.share_action)

    def add_download_button(self):
        self.addAction(self.download_action)

class Model(QStandardItemModel):
    def __init__(self, view):
        super(Model, self).__init__(0, 5)
        self.view = view
        self.gui = self.view.gui
        self.gateway = self.view.gateway
        self.monitor = Monitor(self)
        self.status_dict = {}
        self.setHeaderData(0, Qt.Horizontal, QVariant("Name"))
        self.setHeaderData(1, Qt.Horizontal, QVariant("Status"))
        self.setHeaderData(2, Qt.Horizontal, QVariant("Last sync"))
        self.setHeaderData(3, Qt.Horizontal, QVariant("Size"))
        self.setHeaderData(4, Qt.Horizontal, QVariant("Action"))

        self.icon_blank = QIcon()
        self.icon_up_to_date = QIcon(resource('checkmark.png'))
        self.icon_user = QIcon(resource('user.png'))
        self.icon_folder = QFileIconProvider().icon(QFileInfo(config_dir))
        composite_pixmap = CompositePixmap(
            self.icon_folder.pixmap(256, 256), overlay=None, grayout=True)
        self.icon_folder_gray = QIcon(composite_pixmap)

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
        status = QStandardItem()
        last_sync = QStandardItem()
        size = QStandardItem()
        action = QStandardItem()
        self.appendRow([name, status, last_sync, size, action])
        action_bar = ActionBar(self, basename)
        self.view.setIndexWidget(action.index(), action_bar)
        action.setData(action_bar, Qt.UserRole)
        self.view.hide_drop_label()
        self.set_status(basename, status_data)

    def add_member(self, folder, member):
        items = self.findItems(folder)
        if items:
            items[0].appendRow([QStandardItem(self.icon_user, member)])

    def populate(self):
        for magic_folder in get_nodedirs(self.gateway.magic_folders_dir):
            self.add_folder(magic_folder)
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

    def set_data(self, folder_name, data):
        items = self.findItems(folder_name)
        if items:
            items[0].setData(data, Qt.UserRole)

    def set_status(self, name, status):
        item = self.item(self.findItems(name)[0].row(), 1)
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

    def fade_row(self, folder_name):
        folder_item = self.findItems(folder_name)[0]
        folder_item.setIcon(self.icon_folder_gray)
        row = folder_item.row()
        for i in range(4):
            item = self.item(row, i)
            font = item.font()
            font.setItalic(True)
            item.setFont(font)
            item.setForeground(QColor('gray'))

    def set_last_sync(self, name, text):
        self.item(self.findItems(name)[0].row(), 2).setText(text)

    def set_size(self, name, size):
        item = self.item(self.findItems(name)[0].row(), 3)
        item.setText(naturalsize(size))
        item.setData(size, Qt.UserRole)

    def add_share_button(self, name):
        action_item = self.item(self.findItems(name)[0].row(), 4)
        action_bar = action_item.data(Qt.UserRole)
        action_bar.add_share_button()

    def add_download_button(self, name):
        action_item = self.item(self.findItems(name)[0].row(), 4)
        action_bar = action_item.data(Qt.UserRole)
        action_bar.add_download_button()


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
        self.setModel(Model(self))
        self.setItemDelegate(Delegate(self))

        self.setAcceptDrops(True)
        #self.setColumnWidth(0, 150)
        #self.setColumnWidth(1, 100)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 75)
        self.setColumnWidth(4, 50)
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

    def show_drop_label(self):
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
            self.model().removeRow(self.model().findItems(folder)[0].row())
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

        invite_action = QAction(
            QIcon(resource('invite.png')), 'Enter an Invite Code...', self)
        invite_action.setStatusTip('Enter an Invite Code...')
        invite_action.triggered.connect(self.open_invite_receiver)

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
        self.toolbar.addAction(invite_action)
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

        self.grid_status_updater = LoopingCall(self.set_current_grid_status)

    def populate(self, gateways):
        for gateway in gateways:
            if gateway not in self.gateways:
                self.gateways.append(gateway)
        self.combo_box.populate(self.gateways)
        self.central_widget.populate(self.gateways)
        self.central_widget.addWidget(self.preferences_widget)
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
        view.select_folder()

    def set_current_grid_status(self):
        if self.central_widget.currentWidget() == self.preferences_widget:
            return
        self.status_bar_label.setText(
            self.current_view().model().monitor.grid_status)
        self.gui.systray.update()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.gui.show_setup_form()
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

    def export_recovery_key(self):
        self.show_selected_grid_view()
        gateway = self.current_view().gateway
        dest, _ = QFileDialog.getSaveFileName(
            self, "Select a destination", os.path.join(
                os.path.expanduser('~'), gateway.name + ' Recovery Key.json'))
        if not dest:
            return
        try:
            gateway.export(dest)
        except Exception as e:  # pylint: disable=broad-except
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error exporting Recovery Key")
            msg.setText(str(e))
            msg.exec_()
            return
        if os.path.isfile(dest):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Export successful")
            msg.setText("Recovery Key successfully exported to {}".format(dest))
            msg.exec_()

    def toggle_preferences_widget(self):
        if self.central_widget.currentWidget() == self.preferences_widget:
            self.show_selected_grid_view()
        else:
            self.status_bar.hide()
            for i in range(self.central_widget.count()):
                if self.central_widget.widget(i) == self.preferences_widget:
                    self.central_widget.setCurrentIndex(i)

    def open_invite_receiver(self):
        invite_receiver = InviteReceiver()
        self.active_invite_receivers.append(invite_receiver)
        invite_receiver.done.connect(self.active_invite_receivers.remove)
        invite_receiver.show()

    def open_pair_widget(self):
        gateway = self.combo_box.currentData()
        if gateway:
            pair_widget = ShareWidget(gateway, self.gui)
            self.active_pair_widgets.append(pair_widget)
            pair_widget.done.connect(self.active_pair_widgets.remove)
            pair_widget.show()

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
