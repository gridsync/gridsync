# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
import os
import sys

from PyQt5.QtCore import pyqtSignal, QFileInfo, Qt, QTimer, QThread
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QFileIconProvider, QGridLayout, QGroupBox, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QToolButton, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
import wormhole.errors

from gridsync import resource, APP_NAME, config_dir
from gridsync.crypto import Crypter
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.gui.password import PasswordDialog
from gridsync.invite import Wormhole, InviteCodeLineEdit
from gridsync.msg import error
from gridsync.preferences import set_preference, get_preference
from gridsync.tahoe import TahoeCommandError
from gridsync.util import b58encode, humanized_list


class CompositePixmap(QPixmap):
    def __init__(self, pixmap, overlay=None, grayout=False):
        super(CompositePixmap, self).__init__()
        base_pixmap = QPixmap(pixmap)
        if grayout:
            painter = QPainter(base_pixmap)
            painter.setCompositionMode(painter.CompositionMode_SourceIn)
            painter.fillRect(base_pixmap.rect(), QColor(128, 128, 128, 128))
            painter.end()
        if overlay:
            width = int(base_pixmap.size().width() / 2)
            height = int(base_pixmap.size().height() / 2)
            overlay_pixmap = QPixmap(overlay).scaled(width, height)
            painter = QPainter(base_pixmap)
            painter.drawPixmap(width, height, overlay_pixmap)
            painter.end()
        self.swap(base_pixmap)


class ConnectionSettings(QWidget):
    def __init__(self):
        super(ConnectionSettings, self).__init__()

        self.name_label = QLabel("Grid name:")
        self.name_line_edit = QLineEdit()

        self.introducer_label = QLabel("Introducer fURL:")
        self.introducer_text_edit = QPlainTextEdit()
        self.introducer_text_edit.setMaximumHeight(70)
        self.introducer_text_edit.setTabChangesFocus(True)

        self.mode_label = QLabel("Connection mode:")
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItem("Normal")
        self.mode_combobox.addItem("Tor")
        self.mode_combobox.model().item(1).setEnabled(False)
        self.mode_combobox.addItem("I2P")
        self.mode_combobox.model().item(2).setEnabled(False)

        form = QFormLayout(self)
        form.setWidget(0, QFormLayout.LabelRole, self.name_label)
        form.setWidget(0, QFormLayout.FieldRole, self.name_line_edit)
        form.setWidget(1, QFormLayout.LabelRole, self.introducer_label)
        form.setWidget(1, QFormLayout.FieldRole, self.introducer_text_edit)
        form.setWidget(2, QFormLayout.LabelRole, self.mode_label)
        form.setWidget(2, QFormLayout.FieldRole, self.mode_combobox)


class EncodingParameters(QWidget):
    def __init__(self):
        super(EncodingParameters, self).__init__()

        self.total_label = QLabel("shares.total (N)")
        self.total_spinbox = QSpinBox()
        self.total_spinbox.setRange(1, 255)

        self.needed_label = QLabel("shares.needed (K)")
        self.needed_spinbox = QSpinBox()
        self.needed_spinbox.setRange(1, 255)

        self.happy_label = QLabel("shares.happy (H)")
        self.happy_spinbox = QSpinBox()
        self.happy_spinbox.setRange(1, 255)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1, 1, 4)
        layout.addWidget(self.total_label, 1, 2)
        layout.addWidget(self.total_spinbox, 1, 3)
        layout.addWidget(self.needed_label, 2, 2)
        layout.addWidget(self.needed_spinbox, 2, 3)
        layout.addWidget(self.happy_label, 3, 2)
        layout.addWidget(self.happy_spinbox, 3, 3)

        self.needed_spinbox.valueChanged.connect(self.on_value_changed)
        self.happy_spinbox.valueChanged.connect(self.on_value_changed)
        self.total_spinbox.valueChanged.connect(self.on_total_changed)

    def on_value_changed(self, value):
        if value >= self.total_spinbox.value():
            self.total_spinbox.setValue(value)

    def on_total_changed(self, value):
        if value <= self.needed_spinbox.value():
            self.needed_spinbox.setValue(value)
        if value <= self.happy_spinbox.value():
            self.happy_spinbox.setValue(value)


class RestoreSelector(QWidget):
    def __init__(self, parent):
        super(RestoreSelector, self).__init__()
        self.parent = parent
        self.lineedit = QLineEdit(self)
        self.button = QPushButton("Select file...")
        layout = QGridLayout(self)
        layout.addWidget(self.lineedit, 1, 1)
        layout.addWidget(self.button, 1, 2)

        self.button.clicked.connect(self.select_file)

    def select_file(self):
        dialog = QFileDialog(self, "Select a Recovery Key")
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_():
            selected_file = dialog.selectedFiles()[0]
            self.lineedit.setText(selected_file)
            self.parent.load_from_file(selected_file)


class TahoeConfigForm(QWidget):
    def __init__(self):
        super(TahoeConfigForm, self).__init__()
        self.rootcap = None
        self.settings = {}
        self.crypter = None
        self.crypter_thread = None

        self.connection_settings = ConnectionSettings()
        self.encoding_parameters = EncodingParameters()
        self.restore_selector = RestoreSelector(self)

        connection_settings_gbox = QGroupBox(self)
        connection_settings_gbox.setTitle("Connection settings:")
        connection_settings_gbox_layout = QGridLayout(connection_settings_gbox)
        connection_settings_gbox_layout.addWidget(self.connection_settings)

        encoding_parameters_gbox = QGroupBox(self)
        encoding_parameters_gbox.setTitle("Encoding parameters:")
        encoding_parameters_gbox_layout = QGridLayout(encoding_parameters_gbox)
        encoding_parameters_gbox_layout.addWidget(self.encoding_parameters)

        restore_selector_gbox = QGroupBox(self)
        restore_selector_gbox.setTitle("Restore from Recovery Key:")
        restore_selector_gbox_layout = QGridLayout(restore_selector_gbox)
        restore_selector_gbox_layout.addWidget(self.restore_selector)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        layout = QGridLayout(self)
        layout.addWidget(connection_settings_gbox)
        layout.addWidget(encoding_parameters_gbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        layout.addWidget(restore_selector_gbox)
        layout.addWidget(self.buttonbox)

    def set_name(self, name):
        self.connection_settings.name_line_edit.setText(name)

    def set_introducer(self, introducer):
        self.connection_settings.introducer_text_edit.setPlainText(introducer)

    def set_shares_total(self, shares):
        self.encoding_parameters.total_spinbox.setValue(int(shares))

    def set_shares_needed(self, shares):
        self.encoding_parameters.needed_spinbox.setValue(int(shares))

    def set_shares_happy(self, shares):
        self.encoding_parameters.happy_spinbox.setValue(int(shares))

    def get_name(self):
        return self.connection_settings.name_line_edit.text().strip()

    def get_introducer(self):
        furl = self.connection_settings.introducer_text_edit.toPlainText()
        return furl.lower().strip()

    def get_shares_total(self):
        return self.encoding_parameters.total_spinbox.value()

    def get_shares_needed(self):
        return self.encoding_parameters.needed_spinbox.value()

    def get_shares_happy(self):
        return self.encoding_parameters.happy_spinbox.value()

    def reset(self):
        self.set_name('')
        self.set_introducer('')
        self.set_shares_total(1)
        self.set_shares_needed(1)
        self.set_shares_happy(1)
        self.rootcap = None

    def get_settings(self):
        return {
            'nickname': self.get_name(),
            'introducer': self.get_introducer(),
            'shares-total': self.get_shares_total(),
            'shares-needed': self.get_shares_needed(),
            'shares-happy': self.get_shares_happy(),
            'rootcap': self.rootcap  # Maybe this should be user-settable?
        }

    def load_settings(self, settings_dict):
        for key, value in settings_dict.items():
            if key == 'nickname':
                self.set_name(value)
            elif key == 'introducer':
                self.set_introducer(value)
            elif key == 'shares-total':
                self.set_shares_total(value)
            elif key == 'shares-needed':
                self.set_shares_total(value)
            elif key == 'shares-happy':
                self.set_shares_total(value)
            elif key == 'rootcap':
                self.rootcap = value

    def on_decryption_failed(self, msg):
        self.crypter_thread.quit()
        error(self, "Decryption failed", msg)
        self.crypter_thread.wait()

    def on_decryption_succeeded(self, plaintext):
        self.crypter_thread.quit()
        self.load_settings(json.loads(plaintext.decode('utf-8')))
        self.crypter_thread.wait()

    def decrypt_content(self, data, password):
        self.crypter = Crypter(data, password.encode())
        self.crypter_thread = QThread()
        self.crypter.moveToThread(self.crypter_thread)
        self.crypter.succeeded.connect(self.on_decryption_succeeded)
        self.crypter.failed.connect(self.on_decryption_failed)
        self.crypter_thread.started.connect(self.crypter.decrypt)
        self.crypter_thread.start()
        # TODO: Show progress/busy indicator

    def parse_content(self, content):
        try:
            settings = json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            password, ok = PasswordDialog.get_password(
                self, "Decryption password (required):", show_stats=False)
            if ok:
                self.decrypt_content(content, password)
            return
        self.load_settings(settings)

    def load_from_file(self, path):
        try:
            with open(path, 'rb') as f:
                content = f.read()
        except Exception as e:  # pylint: disable=broad-except
            error(self, type(e).__name__, str(e))
            return
        self.parse_content(content)


class PreferencesWidget(QWidget):

    accepted = pyqtSignal()

    def __init__(self):
        super(PreferencesWidget, self).__init__()
        notifications_groupbox = QGroupBox("Notifications:", self)
        notifications_label = QLabel("Show a desktop notification when...")
        self.checkbox_connection = QCheckBox("Connection status changes")
        self.checkbox_folder = QCheckBox("A folder is updated")
        self.checkbox_invite = QCheckBox("An invite code is used")

        notifications_layout = QGridLayout()
        notifications_layout.addWidget(notifications_label)
        notifications_layout.addWidget(self.checkbox_connection)
        notifications_layout.addWidget(self.checkbox_folder)
        notifications_layout.addWidget(self.checkbox_invite)
        notifications_groupbox.setLayout(notifications_layout)
        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)

        layout = QGridLayout(self)
        layout.addWidget(notifications_groupbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        layout.addWidget(self.buttonbox)

        self.load_preferences()

        self.checkbox_connection.stateChanged.connect(
            self.on_checkbox_connection_changed)
        self.checkbox_folder.stateChanged.connect(
            self.on_checkbox_folder_changed)
        self.checkbox_invite.stateChanged.connect(
            self.on_checkbox_invite_changed)
        self.buttonbox.accepted.connect(self.accepted.emit)

    def load_preferences(self):
        if get_preference('notifications', 'connection') == 'false':
            self.checkbox_connection.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_connection.setCheckState(Qt.Checked)
        if get_preference('notifications', 'folder') == 'false':
            self.checkbox_folder.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_folder.setCheckState(Qt.Checked)
        if get_preference('notifications', 'invite') == 'false':
            self.checkbox_invite.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_invite.setCheckState(Qt.Checked)

    def on_checkbox_connection_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'connection', 'true')
        else:
            set_preference('notifications', 'connection', 'false')

    def on_checkbox_folder_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'folder', 'true')
        else:
            set_preference('notifications', 'folder', 'false')

    def on_checkbox_invite_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'invite', 'true')
        else:
            set_preference('notifications', 'invite', 'false')


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
        self.member_id = ''

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
        self.subtext_label.setText("This could take a few seconds...\n\n")

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
            target = self.gateway
        text = "Your invitation to {} was accepted".format(target)
        self.subtext_label.setText("Invite successful!\n {} at {}".format(
            text, datetime.now().strftime('%H:%M')))
        if get_preference('notifications', 'invite') != 'false':
            self.gui.show_message("Invite successful", text)

    def handle_failure(self, failure):
        msg = QMessageBox(self)
        msg.setStandardButtons(QMessageBox.Retry)
        msg.setEscapeButton(QMessageBox.Retry)
        msg.setIcon(QMessageBox.Warning)
        msg.setDetailedText(str(failure))
        if failure.type == wormhole.errors.ServerConnectionError:
            msg.setText(
                "An error occured while connecting to the server. This could "
                "mean that the server is currently down or that there is some "
                "other problem with your connection. Please try again later.")
            msg.setWindowTitle("Server Connection Error")
        elif failure.type == wormhole.errors.WelcomeError:
            msg.setText(
                "The server negotiating your invitation is online but "
                "is currently refusing to process any invitations. This may "
                "indicate that your version of {} is out-of-date, in which "
                "case you should upgrade to the latest version and try again."
                .format(APP_NAME))
            msg.setWindowTitle("Invite refused")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setEscapeButton(QMessageBox.Ok)
        elif failure.type == wormhole.errors.WrongPasswordError:
            msg.setText(
                "Either your recipient mistyped the invite code or a "
                "potential attacker tried to guess the code and failed.\n\n"
                "You could try again, giving your recipient and any potential "
                "attacker(s) another chance.")
            msg.setWindowTitle("Invite confirmation failed")
        elif failure.type == wormhole.errors.LonelyError:
            return
        else:
            msg.setWindowTitle(str(failure.type.__name__))
            msg.setText(str(failure.value))
        logging.error(str(failure))
        msg.exec_()

    @inlineCallbacks
    def go(self):
        self.wormhole = Wormhole()
        self.wormhole.got_code.connect(self.on_got_code)
        self.wormhole.got_introduction.connect(self.on_got_introduction)
        self.wormhole.send_completed.connect(self.on_send_completed)
        self.settings = self.gateway.get_settings()
        if self.folder_names:
            folders_data = {}
            for folder in self.folder_names:
                self.member_id = b58encode(os.urandom(8))
                try:
                    code = yield self.gateway.magic_folder_invite(
                        folder, self.member_id)
                except TahoeCommandError as err:
                    self.wormhole.close()
                    error(self, "Invite Error", str(err))
                    self.close()
                    return
                folders_data[folder] = {'code': code}
            self.settings['magic-folders'] = folders_data
        self.wormhole.send(self.settings).addErrback(self.handle_failure)

    def closeEvent(self, event):
        if self.code_label.text() and self.progress_bar.value() != 2:
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
                    for folder in self.folder_names:
                        self.gateway.magic_folder_uninvite(
                            folder, self.member_id)
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

    def __init__(self, parent=None):
        super(InviteReceiver, self).__init__()
        self.parent = parent
        self.wormhole = None

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
        self.progressbar.setMaximum(5)  # XXX
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

    def update_progress(self, step, message):
        self.progressbar.setValue(step)
        self.message_label.setText(message)
        if step == 3:
            self.mail_closed_icon.hide()
            self.mail_open_icon.show()
        if step == 4:
            self.mail_open_icon.hide()
            self.folder_icon.show()
        if step == 5:
            self.close_button.show()
            self.done.emit(self)
            self.label.setPixmap(
                QPixmap(resource('green_checkmark.png')).scaled(32, 32))

    @inlineCallbacks
    def parse_message(self, message):
        folders_data = message.get('magic-folders')
        if folders_data:
            folders = []
            for gateway in self.parent.main_window.gateways:
                introducer = gateway.config_get('client', 'introducer.furl')
                if introducer == message['introducer']:
                    tahoe = gateway
            if not tahoe:
                return  # TODO: Create tahoe client to new grid, then link
            for folder, data in folders_data.items():
                self.update_progress(
                    4, 'Joining folder "{}"...'.format(folder))
                collective, personal = data['code'].split('+')
                # TODO: Ensure not already joined, handle name-conflicts
                yield tahoe.link(
                    tahoe.get_rootcap(),
                    folder + ' (collective)',
                    collective
                )
                yield tahoe.link(
                    tahoe.get_rootcap(),
                    folder + ' (personal)',
                    personal
                )
                folders.append(folder)
            if len(folders) == 1:
                target = folders[0]
                text = (
                    'Successfully joined folder "{}"!\n"{}" is now available '
                    'for download'.format(target, target)
                )
            else:
                target = humanized_list(folders, 'folders')
                text = (
                    'Successfully joined {}!\n{} are now available for '
                    'download'.format(target, target)
                )
            self.update_progress(5, text)
        else:
            return  # TODO: Create tahoe client to new grid, then link

    def got_message(self, message):
        self.update_progress(3, "Reading invitation...")
        self.parse_message(message)

    def got_introduction(self):
        self.update_progress(2, "Connected; opening invitation..")

    def go(self, code):
        self.reset()
        self.label.setText(' ')
        self.lineedit.hide()
        self.progressbar.show()
        self.update_progress(1, "Verifying invitation...")
        self.wormhole = Wormhole()
        self.wormhole.got_introduction.connect(self.got_introduction)
        self.wormhole.got_message.connect(self.got_message)
        self.wormhole.receive(code)
        # XXX d.addErrback

    def closeEvent(self, event):
        event.accept()
        self.closed.emit(self)
