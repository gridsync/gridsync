# -*- coding: utf-8 -*-

import os
import sys

from PyQt5.QtCore import QItemSelectionModel, QFileInfo, QSize, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileIconProvider, QGridLayout, QLabel, QMainWindow,
    QMenu, QMessageBox, QShortcut, QSizePolicy, QStackedWidget, QToolButton,
    QWidget)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir
from gridsync.msg import error, info
from gridsync.recovery import RecoveryKeyExporter
from gridsync.gui.history import HistoryView
from gridsync.gui.preferences import PreferencesWidget
from gridsync.gui.welcome import WelcomeDialog
from gridsync.gui.widgets import CompositePixmap
from gridsync.gui.share import InviteReceiver, ShareWidget
from gridsync.gui.view import View


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


class CentralWidget(QStackedWidget):
    def __init__(self, gui):
        super(CentralWidget, self).__init__()
        self.gui = gui
        self.views = []
        self.folders_views = {}
        self.history_views = {}

    def clear(self):
        for _ in range(self.count()):
            self.removeWidget(self.currentWidget())

    def add_folders_view(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform != 'darwin':
            margin_left, _, margin_right, _ = layout.getContentsMargins()
            layout.setContentsMargins(margin_left, 0, margin_right, 0)
        layout.addWidget(view)
        self.addWidget(widget)
        self.views.append(view)
        self.folders_views[gateway] = widget

    def add_history_view(self, gateway):
        view = HistoryView(gateway)
        self.addWidget(view)
        self.history_views[gateway] = view

    def populate(self, gateways):
        self.clear()
        self.folders_views = {}
        self.history_views = {}
        for gateway in gateways:
            self.add_folders_view(gateway)
            self.add_history_view(gateway)


class MainWindow(QMainWindow):
    def __init__(self, gui):
        super(MainWindow, self).__init__()
        self.gui = gui
        self.gateways = []
        self.welcome_dialog = None
        self.recovery_key_exporter = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(500, 300))
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.shortcut_new = QShortcut(QKeySequence.New, self)
        self.shortcut_new.activated.connect(self.show_welcome_dialog)

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
            QIcon(
                CompositePixmap(
                    QIcon(resource('laptop.png')).pixmap(256, 256),
                    resource('green-plus.png')
                )
            ),
            "Connect another device...",
            self
        )
        pair_action.setStatusTip('Connect another device...')
        pair_action.triggered.connect(self.open_pair_widget)

        recovery_action = QAction(
            QIcon(resource('key.png')), "Import/Export Recovery Key...", self)
        recovery_action.setStatusTip("Import/Export Recovery Key...")

        import_action = QAction(QIcon(), 'Import...', self)
        import_action.setStatusTip('Import Recovery Key...')
        import_action.triggered.connect(self.import_recovery_key)

        export_action = QAction(QIcon(), 'Export...', self)
        export_action.setStatusTip('Export Recovery Key...')
        export_action.setShortcut(QKeySequence.Save)
        export_action.triggered.connect(self.export_recovery_key)

        recovery_menu = QMenu(self)
        recovery_menu.addAction(import_action)
        recovery_menu.addAction(export_action)

        recovery_button = QToolButton(self)
        recovery_button.setDefaultAction(recovery_action)
        recovery_button.setMenu(recovery_menu)
        recovery_button.setPopupMode(2)
        recovery_button.setStyleSheet(
            'QToolButton::menu-indicator { image: none }')

        history_action = QAction(
            QIcon(resource('time.png')), 'History', self)
        history_action.setStatusTip('History')
        history_action.triggered.connect(self.on_history_button_clicked)

        self.history_button = QToolButton(self)
        self.history_button.setDefaultAction(history_action)
        self.history_button.setCheckable(True)

        preferences_action = QAction(
            QIcon(resource('preferences.png')), 'Preferences', self)
        preferences_action.setStatusTip('Preferences')
        preferences_action.setShortcut(QKeySequence.Preferences)
        preferences_action.triggered.connect(self.toggle_preferences_widget)

        self.preferences_button = QToolButton(self)
        self.preferences_button.setDefaultAction(preferences_action)
        self.preferences_button.setCheckable(True)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        self.toolbar = self.addToolBar('')
        if sys.platform != 'darwin':
            self.toolbar.setStyleSheet("QToolBar { border: 0px }")
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
        self.toolbar.addWidget(recovery_button)
        #self.toolbar.addAction(export_action)
        self.toolbar.addWidget(self.history_button)
        self.toolbar.addWidget(self.preferences_button)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet('QStatusBar::item { border: 0px; }')
        self.status_bar_label = QLabel('Loading...')
        self.status_bar.addPermanentWidget(self.status_bar_label)

        self.preferences_widget = PreferencesWidget()
        self.preferences_widget.accepted.connect(self.show_folders_view)

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
        self.preferences_widget.load_preferences()

    def current_view(self):
        try:
            w = self.central_widget.folders_views[self.combo_box.currentData()]
        except KeyError:
            return None
        return w.layout().itemAt(0).widget()

    def select_folder(self):
        self.show_folders_view()
        view = self.current_view()
        if view:
            view.select_folder()

    def set_current_grid_status(self):
        if self.central_widget.currentWidget() == self.preferences_widget:
            return
        current_view = self.current_view()
        if not current_view:
            return
        self.status_bar_label.setText(current_view.model().grid_status)
        self.gui.systray.update()

    def show_folders_view(self):
        self.preferences_button.setChecked(False)
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.folders_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()
        self.status_bar.show()

    def show_history_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.history_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()
        self.status_bar.hide()

    def show_welcome_dialog(self):
        if self.welcome_dialog:
            self.welcome_dialog.close()
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.show_welcome_dialog()
        elif self.history_button.isChecked():
            self.show_history_view()
        else:
            self.show_folders_view()
        self.setWindowTitle(
            "{} - {}".format(APP_NAME, self.combo_box.currentData().name)
        )

    def confirm_export(self, path):
        if os.path.isfile(path):
            info(
                self,
                "Export successful",
                "Recovery Key successfully exported to {}".format(path))
        else:
            error(
                self,
                "Error exporting Recovery Key",
                "Destination file not found after export: {}".format(path))

    def export_recovery_key(self, gateway=None):
        self.show_folders_view()
        if not gateway:
            gateway = self.combo_box.currentData()
        self.recovery_key_exporter = RecoveryKeyExporter(self)
        self.recovery_key_exporter.done.connect(self.confirm_export)
        self.recovery_key_exporter.do_export(gateway)

    def import_recovery_key(self):
        # XXX Quick hack for user-testing; change later
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.on_restore_link_activated()

    def on_history_button_clicked(self):
        self.preferences_button.setChecked(False)
        if not self.history_button.isChecked():
            self.history_button.setChecked(True)
            self.show_history_view()
        else:
            self.history_button.setChecked(False)
            self.show_folders_view()

    def toggle_preferences_widget(self):
        self.history_button.setChecked(False)
        if self.central_widget.currentWidget() == self.preferences_widget:
            self.show_folders_view()
        else:
            for i in range(self.central_widget.count()):
                if self.central_widget.widget(i) == self.preferences_widget:
                    self.central_widget.setCurrentIndex(i)
                    self.status_bar.hide()
                    self.preferences_button.setChecked(True)

    def on_invite_received(self, _):
        for view in self.central_widget.views:
            view.model().monitor.scan_rootcap('star.png')

    def on_invite_closed(self, obj):
        try:
            self.active_invite_receivers.remove(obj)
        except ValueError:
            pass

    def open_invite_receiver(self):
        invite_receiver = InviteReceiver(self.gateways)
        invite_receiver.done.connect(self.on_invite_received)
        invite_receiver.closed.connect(self.on_invite_closed)
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
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            view = self.current_view()
            selected = (view.selectedIndexes() if view else None)
            if selected:
                view.confirm_remove(view.get_selected_folders())
        if key == Qt.Key_Escape:
            view = self.current_view()
            selected = (view.selectedIndexes() if view else None)
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
