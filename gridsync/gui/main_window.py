# -*- coding: utf-8 -*-

import json
import os

from PyQt5.QtCore import (
    QItemSelectionModel, QFileInfo, QPropertyAnimation, QSize, Qt, QThread)
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction, QComboBox, QFileDialog, QFileIconProvider, QGridLayout, QLabel,
    QMainWindow, QMenu, QMessageBox, QProgressDialog, QShortcut, QSizePolicy,
    QStackedWidget, QToolButton, QWidget)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir
from gridsync.crypto import Crypter
from gridsync.gui.password import PasswordDialog
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
        self.welcome_dialog = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(500, 300))

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
        self.status_bar_label = QLabel('Loading...')
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
        current_widget = self.central_widget.currentWidget()
        if current_widget:
            view = current_widget.layout().itemAt(0).widget()
            if isinstance(view, View):
                return view
        return None

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

    def show_welcome_dialog(self):
        if self.welcome_dialog:
            self.welcome_dialog.close()
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.show_welcome_dialog()
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
        self.animation.setDuration(5000)  # XXX
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
            self,
            "Encryption passphrase (optional):",
            "A long passphrase will help keep your files safe in the event "
            "that your Recovery Key is ever compromised."
        )
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
