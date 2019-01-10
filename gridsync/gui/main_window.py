# -*- coding: utf-8 -*-

import os
import sys

from PyQt5.QtCore import QItemSelectionModel, QFileInfo, QSize, Qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileIconProvider, QGridLayout, QMainWindow, QMenu,
    QMessageBox, QShortcut, QSizePolicy, QStackedWidget, QToolButton, QWidget)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir
from gridsync.msg import error, info
from gridsync.recovery import RecoveryKeyExporter
from gridsync.gui.history import HistoryView
from gridsync.gui.welcome import WelcomeDialog
from gridsync.gui.widgets import CompositePixmap
from gridsync.gui.share import InviteReceiverDialog, InviteSenderDialog
from gridsync.gui.status import StatusPanel
from gridsync.gui.view import View


class ComboBox(QComboBox):
    def __init__(self):
        super(ComboBox, self).__init__()
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.current_index = 0
        self.insertSeparator(0)
        self.addItem(" Add new...")

        self.activated.connect(self.on_activated)

    def on_activated(self, index):
        if index == self.count() - 1:  # If "Add new..." is selected
            self.setCurrentIndex(self.current_index)
        else:
            self.current_index = index

    def add_gateway(self, gateway):
        basename = os.path.basename(os.path.normpath(gateway.nodedir))
        icon = QIcon(os.path.join(gateway.nodedir, 'icon'))
        if not icon.availableSizes():
            icon = QIcon(resource('tahoe-lafs.png'))
        self.insertItem(0, icon, basename, gateway)
        self.setCurrentIndex(0)
        self.current_index = 0


class CentralWidget(QStackedWidget):
    def __init__(self, gui):
        super(CentralWidget, self).__init__()
        self.gui = gui
        self.views = []
        self.folders_views = {}
        self.history_views = {}

    def add_folders_view(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform == 'darwin':
            # XXX: For some reason, getContentsMargins returns 20 px on macOS..
            layout.setContentsMargins(11, 11, 11, 0)
        else:
            left, _, right, _ = layout.getContentsMargins()
            layout.setContentsMargins(left, 0, right, 0)
        layout.addWidget(view)
        layout.addWidget(StatusPanel(gateway))
        self.addWidget(widget)
        self.views.append(view)
        self.folders_views[gateway] = widget

    def add_history_view(self, gateway):
        view = HistoryView(gateway)
        self.addWidget(view)
        self.history_views[gateway] = view


class MainWindow(QMainWindow):
    def __init__(self, gui):
        super(MainWindow, self).__init__()
        self.gui = gui
        self.gateways = []
        self.welcome_dialog = None
        self.recovery_key_exporter = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(600, 400))
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.shortcut_new = QShortcut(QKeySequence.New, self)
        self.shortcut_new.activated.connect(self.show_welcome_dialog)

        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.select_folder)

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.confirm_quit)

        self.central_widget = CentralWidget(self.gui)
        self.setCentralWidget(self.central_widget)

        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(11)
        else:
            font.setPointSize(8)

        folder_icon_default = QFileIconProvider().icon(QFileInfo(config_dir))
        folder_icon_composite = CompositePixmap(
            folder_icon_default.pixmap(256, 256), resource('green-plus.png'))
        folder_icon = QIcon(folder_icon_composite)

        folder_action = QAction(folder_icon, "Add folder", self)
        folder_action.setToolTip("Add a folder...")
        folder_action.setFont(font)
        folder_action.triggered.connect(self.select_folder)

        invite_action = QAction(
            QIcon(resource('invite.png')), "Enter Code", self)
        invite_action.setToolTip("Enter an Invite Code...")
        invite_action.setFont(font)
        invite_action.triggered.connect(self.open_invite_receiver)

        history_action = QAction(
            QIcon(resource('time.png')), 'History', self)
        history_action.setToolTip("View history")
        history_action.setFont(font)
        history_action.triggered.connect(self.on_history_button_clicked)

        self.history_button = QToolButton(self)
        self.history_button.setDefaultAction(history_action)
        self.history_button.setCheckable(True)
        self.history_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        self.combo_box = ComboBox()
        self.combo_box.currentIndexChanged.connect(self.on_grid_selected)

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        share_action = QAction(QIcon(resource('share.png')), "Share", self)
        share_action.setToolTip("Share...")
        share_action.setFont(font)
        share_action.triggered.connect(self.open_invite_sender_dialog)

        recovery_action = QAction(
            QIcon(resource('key.png')), "Recovery", self)
        recovery_action.setToolTip("Import/Export Recovery Key...")
        recovery_action.setFont(font)

        import_action = QAction(QIcon(), "Import Recovery Key...", self)
        import_action.setToolTip("Import Recovery Key...")
        import_action.triggered.connect(self.import_recovery_key)

        export_action = QAction(QIcon(), "Export Recovery Key...", self)
        export_action.setToolTip("Export Recovery Key...")
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
        recovery_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        preferences_action = QAction(
            QIcon(resource('preferences.png')), "Preferences", self)
        preferences_action.setStatusTip("Preferences")
        preferences_action.setToolTip("Preferences")
        preferences_action.setFont(font)
        preferences_action.setShortcut(QKeySequence.Preferences)
        preferences_action.triggered.connect(self.gui.show_preferences_window)

        self.toolbar = self.addToolBar('')
        if sys.platform != 'darwin':
            self.toolbar.setStyleSheet("""
                QToolBar { border: 0px }
                QToolButton { color: rgb(50, 50, 50) }
            """)
        else:
            self.toolbar.setStyleSheet(
                "QToolButton { color: rgb(50, 50, 50) }")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.toolbar.addAction(folder_action)
        self.toolbar.addAction(invite_action)
        self.toolbar.addWidget(self.history_button)
        self.toolbar.addWidget(spacer_left)
        self.toolbar.addWidget(self.combo_box)
        self.toolbar.addWidget(spacer_right)
        self.toolbar.addAction(share_action)
        self.toolbar.addWidget(recovery_button)
        self.toolbar.addAction(preferences_action)

        if sys.platform != 'win32':  # Text is getting clipped on Windows 10
            for action in self.toolbar.actions():
                widget = self.toolbar.widgetForAction(action)
                if isinstance(widget, QToolButton):
                    widget.setMaximumWidth(68)

        self.active_invite_sender_dialogs = []
        self.active_invite_receiver_dialogs = []

    def populate(self, gateways):
        for gateway in gateways:
            if gateway not in self.gateways:
                self.central_widget.add_folders_view(gateway)
                self.central_widget.add_history_view(gateway)
                self.combo_box.add_gateway(gateway)
                self.gateways.append(gateway)
        self.gui.systray.menu.populate()

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
        current_view = self.current_view()
        if not current_view:
            return
        self.gui.systray.update()

    def show_folders_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.folders_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()

    def show_history_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.history_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()

    def show_welcome_dialog(self):
        if self.welcome_dialog:
            self.welcome_dialog.close()
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.show_welcome_dialog()
        if not self.combo_box.currentData():
            return
        if self.history_button.isChecked():
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
        if not self.history_button.isChecked():
            self.history_button.setChecked(True)
            self.show_history_view()
        else:
            self.history_button.setChecked(False)
            self.show_folders_view()

    def on_invite_received(self, gateway):
        self.populate([gateway])
        for view in self.central_widget.views:
            view.model().monitor.scan_rootcap('star.png')

    def on_invite_closed(self, obj):
        try:
            self.active_invite_receiver_dialogs.remove(obj)
        except ValueError:
            pass

    def open_invite_receiver(self):
        invite_receiver_dialog = InviteReceiverDialog(self.gateways)
        invite_receiver_dialog.done.connect(self.on_invite_received)
        invite_receiver_dialog.closed.connect(self.on_invite_closed)
        invite_receiver_dialog.show()
        self.active_invite_receiver_dialogs.append(invite_receiver_dialog)

    def open_invite_sender_dialog(self):
        gateway = self.combo_box.currentData()
        if gateway:
            view = self.current_view()
            if view:
                invite_sender_dialog = InviteSenderDialog(
                    gateway, self.gui, view.get_selected_folders())
            else:
                invite_sender_dialog = InviteSenderDialog(gateway, self.gui)
            invite_sender_dialog.closed.connect(
                self.active_invite_sender_dialogs.remove)
            invite_sender_dialog.show()
            self.active_invite_sender_dialogs.append(invite_sender_dialog)

    def confirm_quit(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        if sys.platform == 'darwin':
            msg.setText("Are you sure you wish to quit?")
            msg.setInformativeText(
                "If you quit, {} will stop synchronizing your folders until "
                "you run it again.".format(APP_NAME))
        else:
            msg.setWindowTitle("Exit {}?".format(APP_NAME))
            msg.setText(
                "Are you sure you wish to quit? If you quit, {} will stop "
                "synchronizing your folders until you run it again.".format(
                    APP_NAME))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if msg.exec_() == QMessageBox.Yes:
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
