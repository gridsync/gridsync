# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import sys

from PyQt5.QtCore import pyqtSignal, QFileInfo, Qt, QTimer
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QFileIconProvider, QGridLayout, QGroupBox, QLabel, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QSpacerItem, QToolButton, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError
import wormhole.errors

from gridsync import resource, config_dir
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.invite import InviteReceiver, InviteSender
from gridsync.gui.invite import InviteCodeWidget, show_failure
from gridsync.preferences import get_preference
from gridsync.tor import TOR_PURPLE
from gridsync.util import b58encode, humanized_list


class InviteSenderDialog(QDialog):
    done = pyqtSignal(QWidget)
    closed = pyqtSignal(QWidget)

    def __init__(self, gateway, gui, folder_names=None):
        super(InviteSenderDialog, self).__init__()
        self.gateway = gateway
        self.gui = gui
        self.folder_names = folder_names
        self.folder_names_humanized = humanized_list(folder_names, 'folders')
        self.settings = {}
        self.pending_invites = []
        self.use_tor = self.gateway.use_tor

        self.setMinimumSize(500, 300)

        header_icon = QLabel(self)
        if self.folder_names:
            icon = QFileIconProvider().icon(QFileInfo(
                self.gateway.get_magic_folder_directory(self.folder_names[0])))
        else:
            icon = QIcon(os.path.join(gateway.nodedir, 'icon'))
            if not icon.availableSizes():
                icon = QIcon(resource('tahoe-lafs.png'))
        header_icon.setPixmap(icon.pixmap(50, 50))

        header_text = QLabel(self)
        if self.folder_names:
            header_text.setText(self.folder_names_humanized)
        else:
            header_text.setText(self.gateway.name)
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(22)
        else:
            font.setPointSize(18)
        header_text.setFont(font)
        header_text.setAlignment(Qt.AlignCenter)

        header_layout = QGridLayout()
        header_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        header_layout.addWidget(header_icon, 1, 2)
        header_layout.addWidget(header_text, 1, 3)
        header_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)

        self.subtext_label = QLabel(self)
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(13)
        else:
            font.setPointSize(10)
        self.subtext_label.setFont(font)
        self.subtext_label.setStyleSheet("color: grey")
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setAlignment(Qt.AlignCenter)

        self.noise_label = QLabel()
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(20)
        else:
            font.setPointSize(16)
        font.setFamily("Courier")
        font.setStyleHint(QFont.Monospace)
        self.noise_label.setFont(font)
        self.noise_label.setStyleSheet("color: grey")

        self.noise_timer = QTimer()
        self.noise_timer.timeout.connect(
            lambda: self.noise_label.setText(b58encode(os.urandom(16))))
        self.noise_timer.start(75)

        self.code_label = QLabel()
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(22)
        else:
            font.setPointSize(18)
        self.code_label.setFont(font)
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code_label.hide()

        self.box_title = QLabel(self)
        self.box_title.setAlignment(Qt.AlignCenter)
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(20)
        else:
            font.setPointSize(16)
        self.box_title.setFont(font)

        self.box = QGroupBox()
        self.box.setAlignment(Qt.AlignCenter)
        self.box.setStyleSheet('QGroupBox {font-size: 16px}')

        self.copy_button = QToolButton()
        self.copy_button.setIcon(QIcon(resource('copy.png')))
        self.copy_button.setToolTip("Copy to clipboard")
        self.copy_button.setStyleSheet('border: 0px; padding: 0px;')
        self.copy_button.hide()

        box_layout = QGridLayout(self.box)
        box_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        box_layout.addWidget(self.noise_label, 1, 2)
        box_layout.addWidget(self.code_label, 1, 3)
        box_layout.addWidget(self.copy_button, 1, 4)
        box_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)

        self.close_button = QPushButton("Close and cancel invite")
        self.close_button.setAutoDefault(False)

        self.checkmark = QLabel()
        self.checkmark.setPixmap(
            QPixmap(resource('green_checkmark.png')).scaled(32, 32))
        self.checkmark.setAlignment(Qt.AlignCenter)
        self.checkmark.hide()

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network.")
        self.tor_label.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.tor_label.hide()

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addLayout(header_layout, 1, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 2, 1)
        layout.addWidget(self.box_title, 3, 2, 1, 3)
        layout.addWidget(self.checkmark, 3, 3)
        layout.addWidget(
            self.tor_label, 4, 1, 1, 1, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.box, 4, 2, 1, 3)
        layout.addWidget(self.progress_bar, 4, 2, 1, 3)
        layout.addWidget(self.subtext_label, 5, 2, 1, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 6, 1)
        layout.addWidget(self.close_button, 7, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 8, 1)

        self.copy_button.clicked.connect(self.on_copy_button_clicked)
        self.close_button.clicked.connect(self.close)

        self.set_box_title("Generating invite code...")
        self.subtext_label.setText("Creating folder invite(s)...\n\n")

        if self.use_tor:
            self.tor_label.show()
            self.progress_bar.setStyleSheet(
                'QProgressBar::chunk {{ background-color: {}; }}'.format(
                    TOR_PURPLE))

        self.go()  # XXX

    def set_box_title(self, text):
        if sys.platform == 'darwin':
            self.box_title.setText(text)
            self.box_title.show()
        else:
            self.box.setTitle(text)

    def on_copy_button_clicked(self):
        code = self.code_label.text()
        for mode in get_clipboard_modes():
            set_clipboard_text(code, mode)
        self.subtext_label.setText(
            "Copied '{}' to clipboard!\n\n".format(code))

    def on_got_code(self, code):
        self.noise_timer.stop()
        self.noise_label.hide()
        self.set_box_title("Your invite code is:")
        self.code_label.setText(code)
        self.code_label.show()
        self.copy_button.show()
        if self.folder_names:
            if len(self.folder_names) == 1:
                abilities = 'download "{}" and modify its contents'.format(
                    self.folder_names[0])
            else:
                abilities = 'download {} and modify their contents'.format(
                    self.folder_names_humanized)
        else:
            abilities = 'connect to "{}" and upload new folders'.format(
                self.gateway.name)
        self.subtext_label.setText(
            "Entering this code on another device will allow it to {}.\n"
            "This code can only be used once.".format(abilities))

    def on_got_introduction(self):
        if sys.platform == 'darwin':
            self.box_title.hide()
        self.box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(1)
        self.subtext_label.setText("Connection established; sending invite...")

    def on_send_completed(self):
        self.box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(2)
        self.checkmark.show()
        self.close_button.setText("Finish")
        if self.folder_names:
            target = self.folder_names_humanized
        else:
            target = self.gateway.name
        text = "Your invitation to {} was accepted".format(target)
        self.subtext_label.setText("Invite successful!\n {} at {}".format(
            text, datetime.now().strftime('%H:%M')))
        if get_preference('notifications', 'invite') != 'false':
            self.gui.show_message("Invite successful", text)

        if self.folder_names:
            for view in self.gui.main_window.central_widget.views:
                if view.gateway.name == self.gateway.name:
                    for folder in self.folder_names:
                        # Immediately tell the Model that there are at least 2
                        # members for this folder, i.e., that it is now shared
                        view.model().on_members_updated(folder, [None, None])

    def handle_failure(self, failure):
        if failure.type == wormhole.errors.LonelyError:
            return
        logging.error(str(failure))
        show_failure(failure, self)
        self.invite_sender.cancel()
        self.close()

    def on_created_invite(self):
        self.subtext_label.setText("Opening wormhole...\n\n")

    def go(self):
        self.invite_sender = InviteSender(self.use_tor)
        self.invite_sender.created_invite.connect(self.on_created_invite)
        self.invite_sender.got_code.connect(self.on_got_code)
        self.invite_sender.got_introduction.connect(self.on_got_introduction)
        self.invite_sender.send_completed.connect(self.on_send_completed)
        self.invite_sender.send(self.gateway, self.folder_names).addErrback(
            self.handle_failure)

    def closeEvent(self, event):
        if self.code_label.text() and self.progress_bar.value() < 2:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("Cancel invitation?")
            msg.setText(
                'Are you sure you wish to cancel the invitation to "{}"?'
                .format(self.gateway.name))
            msg.setInformativeText(
                'The invite code "{}" will no longer be valid.'.format(
                    self.code_label.text()))
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
            if self.noise_timer.isActive():
                self.noise_timer.stop()
            self.closed.emit(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class InviteReceiverDialog(QDialog):
    done = pyqtSignal(object)  # Tahoe gateway
    closed = pyqtSignal(QWidget)

    def __init__(self, gateways):
        super(InviteReceiverDialog, self).__init__()
        self.gateways = gateways
        self.invite_receiver = None
        self.joined_folders = []

        self.setMinimumSize(500, 300)

        self.mail_closed_icon = QLabel()
        self.mail_closed_icon.setPixmap(
            QPixmap(resource('mail-envelope-closed.png')).scaled(128, 128))
        self.mail_closed_icon.setAlignment(Qt.AlignCenter)

        self.mail_open_icon = QLabel()
        self.mail_open_icon.setPixmap(
            QPixmap(resource('mail-envelope-open.png')).scaled(128, 128))
        self.mail_open_icon.setAlignment(Qt.AlignCenter)

        self.folder_icon = QLabel()
        icon = QFileIconProvider().icon(QFileInfo(config_dir))
        self.folder_icon.setPixmap(icon.pixmap(128, 128))
        self.folder_icon.setAlignment(Qt.AlignCenter)

        self.invite_code_widget = InviteCodeWidget(self)
        self.invite_code_widget.lineedit.go.connect(self.go)  # XXX

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network.")
        self.tor_label.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.checkmark = QLabel()
        self.checkmark.setAlignment(Qt.AlignCenter)
        self.checkmark.setPixmap(
            QPixmap(resource('green_checkmark.png')).scaled(32, 32))

        self.progressbar = QProgressBar(self)
        self.progressbar.setValue(0)
        self.progressbar.setMaximum(6)  # XXX
        self.progressbar.setTextVisible(False)

        self.message_label = QLabel(' ')
        self.message_label.setStyleSheet("color: grey")
        self.message_label.setAlignment(Qt.AlignCenter)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red")
        self.error_label.setAlignment(Qt.AlignCenter)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addWidget(self.mail_closed_icon, 1, 2, 1, 3)
        layout.addWidget(self.mail_open_icon, 1, 2, 1, 3)
        layout.addWidget(self.folder_icon, 1, 2, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addWidget(self.invite_code_widget, 2, 2, 1, 3)
        layout.addWidget(self.checkmark, 2, 3, 1, 1)
        layout.addWidget(
            self.tor_label, 3, 1, 1, 1, Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.progressbar, 3, 2, 1, 3)
        layout.addWidget(self.message_label, 5, 1, 1, 5)
        layout.addWidget(self.error_label, 5, 2, 1, 3)
        layout.addWidget(self.close_button, 6, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 7, 1)

        self.reset()

    def reset(self):
        self.mail_open_icon.hide()
        self.folder_icon.hide()
        self.mail_closed_icon.show()
        self.progressbar.hide()
        self.error_label.setText('')
        self.error_label.hide()
        self.close_button.hide()
        self.tor_label.hide()
        self.checkmark.hide()
        self.progressbar.setStyleSheet('')

    def show_error(self, text):
        self.error_label.setText(text)
        self.message_label.hide()
        self.error_label.show()
        reactor.callLater(3, self.error_label.hide)
        reactor.callLater(3, self.message_label.show)

    def update_progress(self, message):
        step = self.progressbar.value() + 1
        self.progressbar.setValue(step)
        self.message_label.setText(message)
        if step == 3:
            self.mail_closed_icon.hide()
            self.mail_open_icon.show()

    def set_joined_folders(self, folders):
        self.joined_folders = folders
        if folders:
            self.mail_open_icon.hide()
            self.folder_icon.show()

    def on_got_icon(self, path):
        self.mail_open_icon.setPixmap(
            QPixmap(path).scaled(128, 128))
        self.mail_closed_icon.hide()
        self.mail_open_icon.show()

    def on_done(self, gateway):
        self.progressbar.setValue(self.progressbar.maximum())
        self.close_button.show()
        self.checkmark.show()
        self.done.emit(gateway)
        if self.joined_folders and len(self.joined_folders) == 1:
            target = self.joined_folders[0]
            self.message_label.setText(
                'Successfully joined folder "{0}"!\n"{0}" is now available '
                'for download'.format(target))
        elif self.joined_folders:
            target = humanized_list(self.joined_folders, 'folders')
            self.message_label.setText(
                'Successfully joined {0}!\n{0} are now available for '
                'download'.format(target))
        self.close()  # TODO: Cleanup

    def on_grid_already_joined(self, grid_name):
        QMessageBox.information(
            self,
            "Already connected",
            'You are already connected to "{}"'.format(grid_name)
        )
        self.close()

    def got_message(self, _):
        self.update_progress("Reading invitation...")  # 3

    def got_welcome(self):
        self.update_progress("Connected; waiting for message...")  # 2

    def handle_failure(self, failure):
        logging.error(str(failure))
        if failure.type == CancelledError and self.progressbar.value() > 2:
            return
        show_failure(failure, self)
        self.close()

    def go(self, code):
        self.reset()
        self.invite_code_widget.hide()
        self.progressbar.show()
        if self.invite_code_widget.tor_checkbox.isChecked():
            use_tor = True
            self.tor_label.show()
            self.progressbar.setStyleSheet(
                'QProgressBar::chunk {{ background-color: {}; }}'.format(
                    TOR_PURPLE))
        else:
            use_tor = False
        self.update_progress("Verifying invitation...")  # 1
        self.invite_receiver = InviteReceiver(self.gateways, use_tor)
        self.invite_receiver.got_welcome.connect(self.got_welcome)
        self.invite_receiver.got_message.connect(self.got_message)
        self.invite_receiver.grid_already_joined.connect(
            self.on_grid_already_joined)
        self.invite_receiver.update_progress.connect(self.update_progress)
        self.invite_receiver.got_icon.connect(self.on_got_icon)
        self.invite_receiver.joined_folders.connect(self.set_joined_folders)
        self.invite_receiver.done.connect(self.on_done)
        d = self.invite_receiver.receive(code)
        d.addErrback(self.handle_failure)
        reactor.callLater(30, d.cancel)

    def enterEvent(self, event):
        event.accept()
        self.invite_code_widget.lineedit.update_action_button()  # XXX

    def closeEvent(self, event):
        event.accept()
        try:
            self.invite_receiver.cancel()
        except AttributeError:
            pass
        self.closed.emit(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
