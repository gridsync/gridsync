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
from twisted.internet.defer import (
    CancelledError, gatherResults, inlineCallbacks, returnValue)
import wormhole.errors

from gridsync import resource, config_dir
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.invite import (
    get_settings_from_cheatcode, Wormhole, InviteCodeLineEdit, show_failure)
from gridsync.msg import error
from gridsync.preferences import get_preference
from gridsync.setup import SetupRunner, validate_settings
from gridsync.tahoe import TahoeError
from gridsync.util import b58encode, humanized_list


class ShareWidget(QDialog):
    done = pyqtSignal(QWidget)
    closed = pyqtSignal(QWidget)

    def __init__(self, gateway, gui, folder_names=None):  # pylint:disable=too-many-statements
        super(ShareWidget, self).__init__()
        self.gateway = gateway
        self.gui = gui
        self.folder_names = folder_names
        self.folder_names_humanized = humanized_list(folder_names, 'folders')
        self.settings = {}
        self.wormhole = None
        self.pending_invites = []

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
        font.setPointSize(10)
        self.subtext_label.setFont(font)
        self.subtext_label.setStyleSheet("color: grey")
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setAlignment(Qt.AlignCenter)

        self.noise_label = QLabel()
        font = QFont()
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
        font.setPointSize(18)
        self.code_label.setFont(font)
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code_label.hide()

        self.box_title = QLabel(self)
        self.box_title.setAlignment(Qt.AlignCenter)
        font = QFont()
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
        layout.addWidget(self.box, 4, 2, 1, 3)
        layout.addWidget(self.progress_bar, 4, 2, 1, 3)
        layout.addWidget(self.subtext_label, 5, 2, 1, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 6, 1)
        layout.addWidget(self.close_button, 7, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 8, 1)

        self.copy_button.clicked.connect(self.on_copy_button_clicked)
        self.close_button.clicked.connect(self.close)

        self.set_box_title("Generating invite code...")

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

    def handle_failure(self, failure):
        if failure.type == wormhole.errors.LonelyError:
            return
        logging.error(str(failure))
        show_failure(failure, self)
        self.wormhole.close()
        self.close()

    @inlineCallbacks
    def get_folder_invite(self, folder):
        member_id = b58encode(os.urandom(8))
        try:
            code = yield self.gateway.magic_folder_invite(folder, member_id)
        except TahoeError as err:
            code = None
            self.wormhole.close()
            error(self, "Invite Error", str(err))
            self.close()
        returnValue((folder, member_id, code))

    @inlineCallbacks
    def get_folder_invites(self):
        self.subtext_label.setText("Creating folder invite(s)...\n\n")
        folders_data = {}
        tasks = []
        for folder in self.folder_names:
            tasks.append(self.get_folder_invite(folder))
        results = yield gatherResults(tasks)
        for folder, member_id, code in results:
            folders_data[folder] = {'code': code}
            self.pending_invites.append((folder, member_id))
        returnValue(folders_data)

    @inlineCallbacks
    def go(self):
        self.wormhole = Wormhole()
        self.wormhole.got_code.connect(self.on_got_code)
        self.wormhole.got_introduction.connect(self.on_got_introduction)
        self.wormhole.send_completed.connect(self.on_send_completed)
        self.settings = self.gateway.get_settings()
        if self.folder_names:
            folders_data = yield self.get_folder_invites()
            self.settings['magic-folders'] = folders_data
        self.subtext_label.setText("Opening wormhole...\n\n")
        self.wormhole.send(self.settings).addErrback(self.handle_failure)

    def closeEvent(self, event):
        if self.code_label.text() and self.progress_bar.value() < 2:
            reply = QMessageBox.question(
                self, "Cancel invitation?",
                'Are you sure you wish to cancel the invitation to "{}"?\n\n'
                'The invite code "{}" will no longer be valid.'.format(
                    self.gateway.name, self.code_label.text()),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.wormhole.close()
                if self.folder_names:
                    for folder, member_id in self.pending_invites:
                        self.gateway.magic_folder_uninvite(folder, member_id)
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


class InviteReceiver(QWidget):
    done = pyqtSignal(QWidget)
    closed = pyqtSignal(QWidget)

    def __init__(self, gateways):
        super(InviteReceiver, self).__init__()
        self.gateways = gateways
        self.wormhole = None
        self.setup_runner = None
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

        self.label = QLabel("Enter invite code:")
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: grey")
        self.label.setAlignment(Qt.AlignCenter)

        self.lineedit = InviteCodeLineEdit(self)
        self.lineedit.error.connect(self.show_error)
        self.lineedit.go.connect(self.go)

        self.progressbar = QProgressBar(self)
        self.progressbar.setValue(0)
        self.progressbar.setMaximum(6)  # XXX
        self.progressbar.setTextVisible(False)

        self.message_label = QLabel()
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
        layout.addWidget(self.mail_closed_icon, 1, 2, 1, 3)
        layout.addWidget(self.mail_open_icon, 1, 2, 1, 3)
        layout.addWidget(self.folder_icon, 1, 2, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addWidget(self.label, 2, 3, 1, 1)
        layout.addWidget(self.lineedit, 3, 2, 1, 3)
        layout.addWidget(self.progressbar, 3, 2, 1, 3)
        layout.addWidget(self.message_label, 4, 1, 1, 5)
        layout.addWidget(self.error_label, 4, 2, 1, 3)
        layout.addWidget(self.close_button, 5, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 6, 1)

        self.reset()

    def reset(self):
        self.mail_open_icon.hide()
        self.folder_icon.hide()
        self.mail_closed_icon.show()
        self.label.setText("Enter invite code:")
        self.lineedit.show()
        self.lineedit.setText('')
        self.progressbar.hide()
        self.message_label.setText(
            "Invite codes can be used to join a grid or a folder")
        self.error_label.setText('')
        self.error_label.hide()
        self.close_button.hide()

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
        if step == 4:
            self.mail_open_icon.hide()
            self.folder_icon.show()

    def set_joined_folders(self, folders):
        self.joined_folders = folders

    def on_done(self, _):
        self.progressbar.setValue(self.progressbar.maximum())
        self.close_button.show()
        self.done.emit(self)
        self.label.setPixmap(
            QPixmap(resource('green_checkmark.png')).scaled(32, 32))
        if self.joined_folders and len(self.joined_folders) == 1:
            target = self.joined_folders[0]
            self.message_label.setText(
                'Successfully joined folder "{}"!\n"{}" is now available for '
                'download'.format(target, target))
        elif self.joined_folders:
            target = humanized_list(self.joined_folders, 'folders')
            self.message_label.setText(
                'Successfully joined {}!\n{} are now available for '
                'download'.format(target, target))

    def on_grid_already_joined(self, grid_name):
        QMessageBox.information(
            self,
            "Already connected",
            'You are already connected to "{}"'.format(grid_name)
        )
        self.close()

    def got_message(self, message):
        self.update_progress("Reading invitation...")  # 3
        message = validate_settings(message, self.gateways, self)
        self.setup_runner = SetupRunner(self.gateways)
        if not message.get('magic-folders'):
            self.setup_runner.grid_already_joined.connect(
                self.on_grid_already_joined)
        self.setup_runner.update_progress.connect(self.update_progress)
        self.setup_runner.joined_folders.connect(self.set_joined_folders)
        self.setup_runner.done.connect(self.on_done)
        self.setup_runner.run(message)

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
        self.label.setText(' ')
        self.lineedit.hide()
        self.progressbar.show()
        self.update_progress("Verifying invitation...")  # 1
        if code.split('-')[0] == "0":
            settings = get_settings_from_cheatcode(code[2:])
            if settings:
                self.got_message(settings)
                return
        self.wormhole = Wormhole()
        self.wormhole.got_welcome.connect(self.got_welcome)
        self.wormhole.got_message.connect(self.got_message)
        d = self.wormhole.receive(code)
        d.addErrback(self.handle_failure)
        reactor.callLater(30, d.cancel)

    def closeEvent(self, event):
        event.accept()
        try:
            self.wormhole.close()
        except AttributeError:
            pass
        self.closed.emit(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
