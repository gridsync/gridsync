# -*- coding: utf-8 -*-

import logging
import os
import sys
from pathlib import Path

from qtpy.QtCore import QItemSelectionModel, QSize, Qt, QTimer
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtWidgets import (
    QGridLayout,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QStackedWidget,
    QWidget,
)
from twisted.internet import reactor

from gridsync import APP_NAME, CONNECTION_DEFAULT_NICKNAME, features, resource
from gridsync.gui.history import HistoryView
from gridsync.gui.share import InviteReceiverDialog, InviteSenderDialog
from gridsync.gui.status import StatusPanel
from gridsync.gui.toolbar import ToolBar
from gridsync.gui.usage import UsageView
from gridsync.gui.view import View
from gridsync.gui.welcome import WelcomeDialog
from gridsync.msg import error, info
from gridsync.recovery import RecoveryKeyExporter
from gridsync.util import strip_html_tags


class CentralWidget(QStackedWidget):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.views = []
        self.folders_views = {}
        self.history_views = {}
        self.usage_views = {}

        # XXX/TODO: There is no need for multiple StatusPanels. Clean this up.

    def _add_folders_view(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform == "darwin":
            # XXX: For some reason, getContentsMargins returns 20 px on macOS..
            layout.setContentsMargins(11, 11, 11, 0)
        else:
            left, _, right, _ = layout.getContentsMargins()
            layout.setContentsMargins(left, 0, right, 0)
        layout.addWidget(view)
        layout.addWidget(StatusPanel(gateway, self.gui))
        self.addWidget(widget)
        self.views.append(view)
        self.folders_views[gateway] = widget

    def _add_history_view(self, gateway):
        view = HistoryView(gateway, self.gui)
        self.addWidget(view)
        self.history_views[gateway] = view

    def _add_usage_view(self, gateway):
        gateway.load_settings()  # Ensure that zkap_unit_name is read/updated
        view = UsageView(gateway, self.gui)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform == "darwin":
            # XXX: For some reason, getContentsMargins returns 20 px on macOS..
            layout.setContentsMargins(11, 11, 11, 0)
        else:
            left, _, right, _ = layout.getContentsMargins()
            layout.setContentsMargins(left, 0, right, 0)
        layout.addWidget(view)
        layout.addWidget(StatusPanel(gateway, self.gui))
        self.addWidget(widget)
        self.usage_views[gateway] = widget

    def add_gateway(self, gateway):
        self._add_folders_view(gateway)
        self._add_history_view(gateway)
        self._add_usage_view(gateway)


class MainWindow(QMainWindow):
    def __init__(self, gui):
        super().__init__()
        self.gui = gui

        self.gateways = []
        self.welcome_dialog = None
        self.recovery_key_exporter = None
        self.active_invite_sender_dialogs = []
        self.active_invite_receiver_dialogs = []
        self.pending_news_message = ()

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(755, 470))
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.setContextMenuPolicy(Qt.NoContextMenu)

        if sys.platform == "darwin":
            # To disable the broken/buggy "full screen" mode on macOS.
            # See https://github.com/gridsync/gridsync/issues/241
            self.setWindowFlags(Qt.Dialog)

        if features.multiple_grids:
            self.shortcut_new = QShortcut(QKeySequence.New, self)
            self.shortcut_new.activated.connect(self.show_welcome_dialog)

        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.select_folder)

        self.shortcut_preferences = QShortcut(QKeySequence.Preferences, self)
        self.shortcut_preferences.activated.connect(
            self.gui.show_preferences_window
        )

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.confirm_quit)

        self.central_widget = CentralWidget(self.gui)
        self.setCentralWidget(self.central_widget)

        self.toolbar = ToolBar(self)
        self.addToolBar(self.toolbar)
        self.combo_box = self.toolbar.combo_box  # XXX
        self.combo_box.currentIndexChanged.connect(self.on_grid_selected)

        self.toolbar.folder_action_triggered.connect(self.select_folder)
        self.toolbar.enter_invite_action_triggered.connect(
            self.open_invite_receiver
        )
        self.toolbar.create_invite_action_triggered.connect(
            self.open_invite_sender_dialog
        )
        self.toolbar.import_action_triggered.connect(self.import_recovery_key)
        self.toolbar.export_action_triggered.connect(self.export_recovery_key)
        self.toolbar.folders_action_triggered.connect(self.show_folders_view)
        self.toolbar.history_action_triggered.connect(self.show_history_view)
        self.toolbar.usage_action_triggered.connect(self.show_usage_view)

    def populate(self, gateways):
        for gateway in gateways:
            if gateway not in self.gateways:
                self.central_widget.add_gateway(gateway)
                self.combo_box.add_gateway(gateway)
                self.gateways.append(gateway)
                if gateway not in self.gui.core.gateways:
                    self.gui.core.gateways.append(gateway)  # XXX
                gateway.newscap_checker.message_received.connect(
                    self.on_message_received
                )
                gateway.newscap_checker.upgrade_required.connect(
                    self.on_upgrade_required
                )
        if gateways:
            if CONNECTION_DEFAULT_NICKNAME:
                self.toolbar.combo_box.activate(CONNECTION_DEFAULT_NICKNAME)
            self.toolbar.update_actions()  # XXX

    def show_news_message(self, gateway, title, message):
        msgbox = QMessageBox(self)
        msgbox.setWindowModality(Qt.WindowModal)
        icon_filepath = os.path.join(gateway.nodedir, "icon")
        if os.path.exists(icon_filepath):
            msgbox.setIconPixmap(QIcon(icon_filepath).pixmap(64, 64))
        elif os.path.exists(resource("tahoe-lafs.png")):
            msgbox.setIconPixmap(
                QIcon(resource("tahoe-lafs.png")).pixmap(64, 64)
            )
        else:
            msgbox.setIcon(QMessageBox.Information)
        if sys.platform == "darwin":
            msgbox.setText(title)
            msgbox.setInformativeText(message)
        else:
            msgbox.setWindowTitle(title)
            msgbox.setText(message)
        msgbox.show()
        try:
            self.gui.unread_messages.remove((gateway, title, message))
        except ValueError:
            return
        self.gui.systray.update()

    def _maybe_show_news_message(self, gateway, title, message):
        self.gui.unread_messages.append((gateway, title, message))
        self.gui.systray.update()
        if self.isVisible():
            self.show_news_message(gateway, title, message)
        else:
            self.pending_news_message = (gateway, title, message)

    def on_message_received(self, gateway, message):
        title = "New message from {}".format(gateway.name)
        self.gui.show_message(
            title, strip_html_tags(message.replace("<p>", "\n\n"))
        )
        self._maybe_show_news_message(gateway, title, message)

    def on_upgrade_required(self, gateway):
        title = "Upgrade required"
        message = (
            "A message was received from {} in an unsupported format. This "
            "suggests that you are running an out-of-date version of {}.\n\n"
            "To avoid seeing this warning, please upgrade to the latest "
            "version.".format(gateway.name, APP_NAME)
        )
        self._maybe_show_news_message(gateway, title, message)

    def current_view(self):
        try:
            w = self.central_widget.folders_views[self.combo_box.currentData()]
        except KeyError:
            return None
        return w.layout().itemAt(0).widget()

    def select_folder(self):
        view = self.current_view()
        if view:
            view.select_folder()

    def set_current_grid_status(self):
        current_view = self.current_view()
        if not current_view:
            return
        self.gui.systray.update()
        self.toolbar.update_actions()  # XXX

    def show_folders_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.folders_views[self.combo_box.currentData()]
            )
        except KeyError:
            return
        self.set_current_grid_status()

    def show_history_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.history_views[self.combo_box.currentData()]
            )
        except KeyError:
            return
        self.set_current_grid_status()

    def show_usage_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.usage_views[self.combo_box.currentData()]
            )
        except KeyError:
            return
        self.set_current_grid_status()

    def show_welcome_dialog(self):
        if self.welcome_dialog:
            self.welcome_dialog.close()
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:  # XXX
            self.show_welcome_dialog()
        if not self.combo_box.currentData():
            return
        if self.toolbar.history_button.isChecked():  # XXX
            self.show_history_view()
        else:
            self.show_folders_view()
            self.toolbar.folders_button.setChecked(True)  # XXX
        if features.multiple_grids:
            self.setWindowTitle(
                "{} - {}".format(APP_NAME, self.combo_box.currentData().name)
            )
        self.toolbar.update_actions()  # XXX

    def confirm_exported(self, path, gateway):
        if os.path.isfile(path):
            Path(gateway.nodedir, "private", "recovery_key_exported").touch(
                exist_ok=True
            )
            gateway.recovery_key_exported = True
            logging.info("Recovery Key successfully created")
            info(
                self,
                "Recovery Key created",
                f"Recovery Key successfully saved to {path}",
            )
        else:
            logging.error("Error creating Recovery Key; file not found.")
            error(
                self,
                "Error creating Recovery Key",
                f"Destination file not found after saving: {path}",
            )

    def export_recovery_key(self, gateway=None):
        if not gateway:
            gateway = self.combo_box.currentData()
        self.recovery_key_exporter = RecoveryKeyExporter(self)
        self.recovery_key_exporter.done.connect(
            lambda path: self.confirm_exported(path, gateway)
        )
        self.recovery_key_exporter.do_export(gateway)

    def import_recovery_key(self):
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.on_restore_link_activated()

    def prompt_for_export(self, gateway):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        button_export = msg.button(QMessageBox.Yes)
        button_export.setText("&Create...")
        button_skip = msg.button(QMessageBox.No)
        button_skip.setText("&Skip")
        msg.setWindowTitle("Create Recovery Key?")
        msg.setText(
            f"Before uploading any folders to {gateway.name}, it is "
            "recommended that you create a Recovery Key and store it in a safe"
            " location (such as an encrypted USB drive or password manager)."
        )
        msg.setInformativeText(
            f"{gateway.name} does not have access to your folders, and cannot "
            "restore access to them. But with a Recovery Key, you can restore "
            "access to uploaded folders in case something goes wrong (e.g., "
            "hardware failure, accidental data-loss).<p><p><a href=https://"
            "github.com/gridsync/gridsync/blob/master/docs/recovery-keys.md>"
            "More information...</a>"
        )
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            self.export_recovery_key(gateway)

    def on_invite_received(self, gateway):
        self.populate([gateway])

    def on_invite_closed(self, obj):
        try:
            self.active_invite_receiver_dialogs.remove(obj)
        except ValueError:
            pass

    def open_invite_receiver(self):
        invite_receiver_dialog = InviteReceiverDialog(self.gateways)
        invite_receiver_dialog.completed.connect(self.on_invite_received)
        invite_receiver_dialog.closed.connect(self.on_invite_closed)
        invite_receiver_dialog.show()
        self.active_invite_receiver_dialogs.append(invite_receiver_dialog)

    def open_invite_sender_dialog(self):
        gateway = self.combo_box.currentData()
        if gateway:
            view = self.current_view()
            if view:
                invite_sender_dialog = InviteSenderDialog(
                    gateway, self.gui, view.get_selected_folders()
                )
            else:
                invite_sender_dialog = InviteSenderDialog(gateway, self.gui)
            invite_sender_dialog.closed.connect(
                self.active_invite_sender_dialogs.remove
            )
            invite_sender_dialog.show()
            self.active_invite_sender_dialogs.append(invite_sender_dialog)

    def _is_folder_syncing(self) -> bool:
        for model in [view.model() for view in self.central_widget.views]:
            if model.is_folder_syncing():
                return True
        return False

    def _is_zkap_auth_required(self) -> bool:
        for gateway in self.gateways:
            if gateway.zkap_auth_required:
                return True
        return False

    def confirm_quit(self):
        msg = QMessageBox(self)
        if self._is_folder_syncing():
            msg.setIcon(QMessageBox.Warning)
            informative_text = (
                "One or more folders are currently syncing. If you quit, any "
                "pending upload or download operations will be cancelled "
                "until you launch {} again.".format(APP_NAME)
            )
        elif self._is_zkap_auth_required():
            msg.setIcon(QMessageBox.Warning)
            # XXX/TODO: Include lease-renewal period/schedule? e.g.,
            # "Failing to to launch {APP_NAME} within X days..."?
            informative_text = (
                f"If you quit, {APP_NAME} will stop renewing the data that "
                f"you have previously uploaded. Failing to launch {APP_NAME} "
                "for extended periods of time may result in data-loss."
            )
        else:
            msg.setIcon(QMessageBox.Question)
            informative_text = (
                "If you quit, {} will stop synchronizing your folders until "
                "you launch it again.".format(APP_NAME)
            )
        if sys.platform == "darwin":
            msg.setText("Are you sure you wish to quit?")
            msg.setInformativeText(informative_text)
        else:
            msg.setWindowTitle("Exit {}?".format(APP_NAME))
            msg.setText(
                "Are you sure you wish to quit? {}".format(informative_text)
            )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if msg.exec_() == QMessageBox.Yes:
            if sys.platform == "win32":
                self.gui.systray.hide()
            reactor.stop()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            view = self.current_view()
            selected = view.selectedIndexes() if view else []
            if selected:
                view.confirm_stop_syncing(view.get_selected_folders())
        if key == Qt.Key_Escape:
            view = self.current_view()
            selected = view.selectedIndexes() if view else []
            if selected:
                for index in selected:
                    view.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )
            elif self.gui.systray.isSystemTrayAvailable():
                self.hide()

    def closeEvent(self, event):
        if self.gui.systray.isSystemTrayAvailable():
            event.accept()
        else:
            event.ignore()
            self.confirm_quit()

    def showEvent(self, _):
        if self.pending_news_message:
            gateway, title, message = self.pending_news_message
            self.pending_news_message = ()
            QTimer.singleShot(
                0, lambda: self.show_news_message(gateway, title, message)
            )
