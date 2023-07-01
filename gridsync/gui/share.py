# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import wormhole.errors
from qtpy.QtCore import QEvent, QFileInfo, Qt, Signal
from qtpy.QtGui import QCloseEvent, QIcon, QKeyEvent
from qtpy.QtWidgets import (
    QDialog,
    QFileIconProvider,
    QGridLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QWidget,
)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError
from twisted.python.failure import Failure

from gridsync import config_dir, resource
from gridsync.gui.font import Font
from gridsync.gui.invite import (
    InviteCodeBox,
    InviteCodeWidget,
    InviteHeaderWidget,
    show_failure,
)
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.widgets import HSpacer, VSpacer
from gridsync.invite import InviteReceiver, InviteSender
from gridsync.preferences import get_preference
from gridsync.tahoe import Tahoe
from gridsync.tor import TOR_PURPLE
from gridsync.util import humanized_list

if TYPE_CHECKING:
    from gridsync.gui import AbstractGui


class InviteSenderDialog(QDialog):
    completed = Signal(QWidget)
    closed = Signal(QWidget)

    def __init__(
        self,
        gateway: Tahoe,
        gui: AbstractGui,
        folder_names: Optional[list] = None,
    ) -> None:
        super().__init__()
        self.gateway = gateway
        self.gui = gui
        self.folder_names = folder_names
        if folder_names:
            self.folder_names_humanized = humanized_list(
                folder_names, "folders"
            )
        else:
            self.folder_names_humanized = ""
        self.settings: dict = {}
        self.pending_invites: list = []
        self.use_tor = self.gateway.use_tor

        self.setMinimumSize(500, 300)

        self.header_widget = InviteHeaderWidget(self)

        if self.folder_names:
            icon = QFileIconProvider().icon(
                QFileInfo(
                    self.gateway.magic_folder.get_directory(
                        self.folder_names[0]
                    )
                )
            )
        else:
            icon = QIcon(os.path.join(gateway.nodedir, "icon"))
            if not icon.availableSizes():
                icon = QIcon(resource("tahoe-lafs.png"))
        self.header_widget.set_icon(icon)

        if self.folder_names_humanized:
            self.header_widget.set_text(self.folder_names_humanized)
        else:
            self.header_widget.set_text(self.gateway.name)

        self.subtext_label = QLabel(self)
        self.subtext_label.setFont(Font(10))
        self.subtext_label.setStyleSheet("color: grey")
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setAlignment(Qt.AlignCenter)

        self.code_box = InviteCodeBox(self)

        self.close_button = QPushButton("Close and cancel invite")
        self.close_button.setAutoDefault(False)

        self.checkmark = QLabel()
        self.checkmark.setPixmap(Pixmap("green_checkmark.png", 32))
        self.checkmark.setAlignment(Qt.AlignCenter)
        self.checkmark.hide()

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network."
        )
        self.tor_label.setPixmap(Pixmap("tor-onion.png", 24))
        self.tor_label.hide()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 0, 0)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.header_widget, 1, 3)
        layout.addItem(VSpacer(), 2, 1)
        layout.addWidget(self.checkmark, 3, 3)
        layout.addWidget(
            self.tor_label, 4, 1, 1, 1, Qt.AlignRight | Qt.AlignVCenter
        )
        layout.addWidget(self.code_box, 4, 2, 1, 3)
        layout.addWidget(self.progress_bar, 4, 2, 1, 3)
        layout.addWidget(self.subtext_label, 5, 2, 1, 3)
        layout.addItem(VSpacer(), 6, 1)
        layout.addWidget(self.close_button, 7, 3)
        layout.addItem(VSpacer(), 8, 1)

        self.code_box.copy_button.clicked.connect(self.on_copy_button_clicked)
        self.close_button.clicked.connect(self.close)

        self.code_box.show_noise()
        self.subtext_label.setText("Creating folder invite(s)...\n\n")

        if self.use_tor:
            self.tor_label.show()
            self.progress_bar.setStyleSheet(
                "QProgressBar::chunk {{ background-color: {}; }}".format(
                    TOR_PURPLE
                )
            )

        self.go()  # XXX

    def on_copy_button_clicked(self) -> None:
        code = self.code_box.code_label.text()
        self.subtext_label.setText(
            "Copied '{}' to clipboard!\n\n".format(code)
        )

    def on_got_code(self, code: str) -> None:
        self.code_box.show_code(code)
        if self.folder_names:
            if len(self.folder_names) == 1:
                abilities = 'download "{}" and modify its contents'.format(
                    self.folder_names[0]
                )
            else:
                abilities = "download {} and modify their contents".format(
                    self.folder_names_humanized
                )
        else:
            abilities = 'connect to "{}" and upload new folders'.format(
                self.gateway.name
            )
        self.subtext_label.setText(
            "Entering this code on another device will allow it to {}.\n"
            "This code can only be used once.".format(abilities)
        )

    def on_got_introduction(self) -> None:
        self.code_box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(1)
        self.subtext_label.setText("Connection established; sending invite...")

    def on_send_completed(self) -> None:
        self.code_box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(2)
        self.checkmark.show()
        self.close_button.setText("Finish")
        if self.folder_names:
            target = self.folder_names_humanized
        else:
            target = self.gateway.name
        text = "Your invitation to {} was accepted".format(target)
        self.subtext_label.setText(
            "Invite successful!\n {} at {}".format(
                text, datetime.now().strftime("%H:%M")
            )
        )
        if get_preference("notifications", "invite") != "false":
            self.gui.show_message("Invite successful", text)

        if self.folder_names:
            for view in self.gui.main_window.central_widget.views:
                if view.gateway.name == self.gateway.name:
                    for folder in self.folder_names:
                        # Immediately tell the Model that there are at least 2
                        # members for this folder, i.e., that it is now shared
                        model = view.get_model()
                        model.on_members_updated(folder, [None, None])

    def handle_failure(self, failure: Failure) -> None:
        if failure.type == wormhole.errors.LonelyError:
            return
        logging.error(str(failure))
        show_failure(failure, self)
        self.invite_sender.cancel()
        self.close()

    def on_created_invite(self) -> None:
        self.subtext_label.setText("Opening wormhole...\n\n")

    def go(self) -> None:
        self.invite_sender = InviteSender(self.use_tor)
        self.invite_sender.created_invite.connect(self.on_created_invite)
        self.invite_sender.got_code.connect(self.on_got_code)
        self.invite_sender.got_introduction.connect(self.on_got_introduction)
        self.invite_sender.send_completed.connect(self.on_send_completed)
        self.invite_sender.send(self.gateway, self.folder_names).addErrback(
            self.handle_failure
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.code_box.code_label.text() and self.progress_bar.value() < 2:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Cancel invitation?")
            msg.setText(
                'Are you sure you wish to cancel the invitation to "{}"?'.format(
                    self.gateway.name
                )
            )
            msg.setInformativeText(
                'The invite code "{}" will no longer be valid.'.format(
                    # self.code_label.text()
                    self.code_box.code_label.text()
                )
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            if msg.exec_() == QMessageBox.Yes:
                self.invite_sender.cancel()
                event.accept()
                self.closed.emit(self)
            else:
                event.ignore()
        else:
            event.accept()
            if self.code_box.noise_timer.isActive():  # XXX
                self.code_box.noise_timer.stop()
            self.closed.emit(self)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()


class InviteReceiverDialog(QDialog):
    completed = Signal(object)  # Tahoe gateway
    closed = Signal(QWidget)

    def __init__(self, gateways: list) -> None:
        super().__init__()
        self.gateways = gateways
        self.invite_receiver = InviteReceiver([])
        self.joined_folders: list = []

        self.setMinimumSize(500, 300)

        self.mail_closed_icon = QLabel()
        self.mail_closed_icon.setAlignment(Qt.AlignCenter)
        self.mail_closed_icon.setPixmap(
            Pixmap("mail-envelope-closed.png", 128)
        )

        self.mail_open_icon = QLabel()
        self.mail_open_icon.setAlignment(Qt.AlignCenter)
        self.mail_open_icon.setPixmap(Pixmap("mail-envelope-open.png", 128))

        self.folder_icon = QLabel()
        icon = QFileIconProvider().icon(QFileInfo(config_dir))
        self.folder_icon.setPixmap(icon.pixmap(128, 128))
        self.folder_icon.setAlignment(Qt.AlignCenter)

        self.invite_code_widget = InviteCodeWidget(self)
        self.invite_code_widget.lineedit.go.connect(self.go)  # XXX

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network."
        )
        self.tor_label.setPixmap(Pixmap("tor-onion.png", 24))

        self.checkmark = QLabel()
        self.checkmark.setAlignment(Qt.AlignCenter)
        self.checkmark.setPixmap(Pixmap("green_checkmark.png", 32))

        self.progressbar = QProgressBar(self)
        self.progressbar.setValue(0)
        self.progressbar.setMaximum(6)  # XXX
        self.progressbar.setTextVisible(False)

        self.message_label = QLabel(" ")
        self.message_label.setStyleSheet("color: grey")
        self.message_label.setAlignment(Qt.AlignCenter)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 0, 0)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addWidget(self.mail_closed_icon, 1, 2, 1, 3)
        layout.addWidget(self.mail_open_icon, 1, 2, 1, 3)
        layout.addWidget(self.folder_icon, 1, 2, 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.invite_code_widget, 2, 2, 1, 3)
        layout.addWidget(self.checkmark, 2, 3, 1, 1)
        layout.addWidget(
            self.tor_label, 3, 1, 1, 1, Qt.AlignRight | Qt.AlignVCenter
        )
        layout.addWidget(self.progressbar, 3, 2, 1, 3)
        layout.addWidget(self.message_label, 5, 1, 1, 5)
        layout.addWidget(self.close_button, 6, 3)
        layout.addItem(VSpacer(), 7, 1)

        self.reset()

    def reset(self) -> None:
        self.mail_open_icon.hide()
        self.folder_icon.hide()
        self.mail_closed_icon.show()
        self.progressbar.hide()
        self.invite_code_widget.clear_error()
        self.close_button.hide()
        self.tor_label.hide()
        self.checkmark.hide()
        self.progressbar.setStyleSheet("")

    def show_error(self, text: str) -> None:
        self.invite_code_widget.show_error(text)
        self.message_label.hide()
        # mypy: 'Module has no attribute "callLater"'
        reactor.callLater(3, self.invite_code_widget.clear_error)  # type: ignore
        reactor.callLater(3, self.message_label.show)  # type: ignore

    def update_progress(self, message: str) -> None:
        step = self.progressbar.value() + 1
        self.progressbar.setValue(step)
        self.message_label.setText(message)
        if step == 3:
            self.mail_closed_icon.hide()
            self.mail_open_icon.show()

    def set_joined_folders(self, folders: list) -> None:
        self.joined_folders = folders
        if folders:
            self.mail_open_icon.hide()
            self.folder_icon.show()

    def on_got_icon(self, path: str) -> None:
        self.mail_open_icon.setPixmap(Pixmap(path, 128))
        self.mail_closed_icon.hide()
        self.mail_open_icon.show()

    def on_done(self, gateway: Tahoe) -> None:
        self.progressbar.setValue(self.progressbar.maximum())
        self.close_button.show()
        self.checkmark.show()
        self.completed.emit(gateway)
        if self.joined_folders and len(self.joined_folders) == 1:
            target = self.joined_folders[0]
            self.message_label.setText(
                'Successfully joined folder "{0}"!\n"{0}" is now available '
                "for download".format(target)
            )
        elif self.joined_folders:
            target = humanized_list(self.joined_folders, "folders")
            self.message_label.setText(
                "Successfully joined {0}!\n{0} are now available for "
                "download".format(target)
            )
        self.close()  # TODO: Cleanup

    def on_grid_already_joined(self, grid_name: str) -> None:
        QMessageBox.information(
            self,
            "Already connected",
            'You are already connected to "{}"'.format(grid_name),
        )
        self.close()

    def got_message(self, _: dict) -> None:
        self.update_progress("Reading invitation...")  # 3

    def got_welcome(self) -> None:
        self.update_progress("Connected; waiting for message...")  # 2

    def handle_failure(self, failure: Failure) -> None:
        logging.error(str(failure))
        if failure.type == CancelledError and self.progressbar.value() > 2:
            return
        show_failure(failure, self)
        self.close()

    def go(self, code: str) -> None:
        self.reset()
        self.invite_code_widget.hide()
        self.progressbar.show()
        if self.invite_code_widget.tor_checkbox.isChecked():
            use_tor = True
            self.tor_label.show()
            self.progressbar.setStyleSheet(
                "QProgressBar::chunk {{ background-color: {}; }}".format(
                    TOR_PURPLE
                )
            )
        else:
            use_tor = False
        self.update_progress("Verifying invitation...")  # 1
        self.invite_receiver = InviteReceiver(self.gateways, use_tor)
        self.invite_receiver.got_welcome.connect(self.got_welcome)
        self.invite_receiver.got_message.connect(self.got_message)
        self.invite_receiver.grid_already_joined.connect(
            self.on_grid_already_joined
        )
        self.invite_receiver.update_progress.connect(self.update_progress)
        self.invite_receiver.got_icon.connect(self.on_got_icon)
        self.invite_receiver.joined_folders.connect(self.set_joined_folders)
        self.invite_receiver.done.connect(self.on_done)
        d = self.invite_receiver.receive(code)
        d.addErrback(self.handle_failure)
        # mypy: 'Module has no attribute "callLater"'
        reactor.callLater(30, d.cancel)  # type: ignore

    def enterEvent(self, event: QEvent) -> None:
        event.accept()
        self.invite_code_widget.lineedit.update_action_button()  # XXX

    def closeEvent(self, event: QCloseEvent) -> None:
        event.accept()
        try:
            self.invite_receiver.cancel()
        except AttributeError:
            pass
        self.closed.emit(self)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
