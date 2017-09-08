# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
import os
import sys

from PyQt5.QtCore import pyqtSignal, QFileInfo, Qt
from PyQt5.QtGui import QFont, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialogButtonBox, QFileDialog, QFormLayout,
    QFileIconProvider, QGridLayout, QGroupBox, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QToolButton, QWidget)
import wormhole.errors

from gridsync import resource, APP_NAME
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.invite import Wormhole
from gridsync.preferences import set_preference, get_preference


class CompositePixmap(QPixmap):
    def __init__(self, pixmap, overlay=None):
        super(CompositePixmap, self).__init__()
        base_pixmap = QPixmap(pixmap)
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

        self.name_label = QLabel("Name:")
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
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_():
            selected_file = dialog.selectedFiles()[0]
            self.lineedit.setText(selected_file)
            self.parent.load_from_json_file(selected_file)


class TahoeConfigForm(QWidget):
    def __init__(self):
        super(TahoeConfigForm, self).__init__()
        self.rootcap = None
        self.settings = {}

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

    def load_from_json_file(self, path):
        try:
            with open(path, 'r') as f:
                settings = json.loads(f.read())
        except json.decoder.JSONDecodeError as err:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Error importing file")
            msg.setText(str(err))
            msg.exec_()
            self.reset()
            return
        for key, value in settings.items():
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


class ShareWidget(QWidget):
    done = pyqtSignal(QWidget)

    def __init__(self, gateway, gui, folder_name=None):  # pylint:disable=too-many-statements
        super(ShareWidget, self).__init__()
        self.gateway = gateway
        self.gui = gui
        self.folder_name = folder_name
        self.settings = {}
        self.wormhole = None
        self.magic_folder_gateway = None
        self.recipient = ''

        if self.folder_name:
            self.magic_folder_gateway = self.gateway.get_magic_folder_gateway(
                folder_name)

        self.icon_label = QLabel(self)
        if self.magic_folder_gateway:
            icon = QFileIconProvider().icon(QFileInfo(
                self.magic_folder_gateway.magic_folder_path))
        else:
            icon = QIcon(os.path.join(gateway.nodedir, 'icon'))
            if not icon.availableSizes():
                icon = QIcon(resource('tahoe-lafs.png'))
        self.icon_label.setPixmap(icon.pixmap(50, 50))

        self.name_label = QLabel(self)
        if self.magic_folder_gateway:
            self.name_label.setText(self.folder_name)
        else:
            self.name_label.setText(self.gateway.name)

        font = QFont()
        font.setPointSize(18)
        self.name_label.setFont(font)
        self.name_label.setAlignment(Qt.AlignCenter)

        label_layout = QGridLayout()
        label_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        label_layout.addWidget(self.icon_label, 1, 2)
        label_layout.addWidget(self.name_label, 1, 3)
        label_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)

        self.recipient_label = QLabel("Recipient name:")
        #font = QFont()
        #font.setPointSize(12)
        #self.recipient_label.setFont(font)

        self.lineedit = QLineEdit(self)
        #font = QFont()
        #font.setPointSize(12)
        #self.lineedit.setFont(font)
        self.lineedit.setPlaceholderText('e.g., "Bob"')

        self.lineedit_layout = QGridLayout()
        self.lineedit_layout.addItem(
                QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        self.lineedit_layout.addWidget(self.recipient_label, 1, 2)
        self.lineedit_layout.addWidget(self.lineedit, 1, 3)
        self.lineedit_layout.addItem(
                QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)

        pair_instructions = (
            'To connect another device to {}, install {} on that device and '
            'click the "Generate invite code" button below. The code that '
            'appears can then be entered on the new device, allowing it to '
            'connect to {} and upload new folders.\n\n'
            'This operation will not disclose or share any of your existing '
            'folders with the new device.'.format(
                self.gateway.name, APP_NAME, self.gateway.name))

        pair_subtext = (
            'Only enter invite codes on devices you trust; '
            'access to {} cannot be revoked once granted.'.format(
                self.gateway.name))

        share_folder_instructions = (
            # "To invite another user to {}"?
            'To share the folder "{}" with another user of {}, enter a name '
            'for that person below and click the "Generate invite code" '
            'button. The code that appears can then be entered by that '
            'person, allowing them to download a copy of {} and add new files '
            'to yours.'.format(self.folder_name, APP_NAME, self.folder_name))
            # "Any future changes made to this folder will be synchronized between other members"?

        share_folder_subtext = (
            'Only extend invites to persons that you trust; '
            'granting access to {} is irrevocable and will also allow the '
            'recipient to upload additional folders to {}'.format(
                self.folder_name, self.gateway.name))

        self.instructions = QLabel(self)
        self.instructions.setWordWrap(True)
        if self.magic_folder_gateway:
            self.instructions.setText(share_folder_instructions)
        else:
            self.instructions.setText(pair_instructions)

        self.instructions_box = QGroupBox()
        instructions_box_layout = QGridLayout(self.instructions_box)
        instructions_box_layout.addWidget(self.instructions)
        if self.magic_folder_gateway:
            instructions_box_layout.addLayout(self.lineedit_layout, 2, 0)
        else:
            self.lineedit.hide()

        self.subtext_label = QLabel(self)
        font = QFont()
        font.setPointSize(10)
        self.subtext_label.setFont(font)
        self.subtext_label.setStyleSheet("color: grey")
        self.subtext_label.setWordWrap(True)
        self.subtext_label.setAlignment(Qt.AlignCenter)
        if self.magic_folder_gateway:
            self.subtext_label.setText(share_folder_subtext)
        else:
            self.subtext_label.setText(pair_subtext)

        self.waiting_label = QLabel("Generating invite code...")

        self.code_label = QLabel()
        font = QFont()
        font.setPointSize(18)
        self.code_label.setFont(font)
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.copy_button = QToolButton()
        self.copy_button.setIcon(QIcon(resource('paste.png')))
        self.copy_button.setToolTip("Copy to clipboard")
        self.copy_button.setStyleSheet('border: 0px; padding: 0px;')

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()

        self.code_box_title = QLabel(self)
        self.code_box_title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        self.code_box_title.setFont(font)

        self.code_box = QGroupBox()
        self.code_box.setAlignment(Qt.AlignCenter)
        self.code_box.setStyleSheet('QGroupBox {font-size: 16px}')
        box_layout = QGridLayout(self.code_box)
        box_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        box_layout.addWidget(self.waiting_label, 1, 2)
        box_layout.addWidget(self.code_label, 1, 3)
        box_layout.addWidget(self.copy_button, 1, 4)
        box_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)

        self.generate_button = QPushButton("Generate invite code")

        self.close_button = QPushButton("Close and cancel")

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addLayout(label_layout, 1, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 2, 1)
        layout.addWidget(self.instructions_box, 3, 2, 1, 3)
        layout.addWidget(self.code_box_title, 3, 2, 1, 3)
        layout.addWidget(self.code_box, 4, 2, 1, 3)
        layout.addWidget(self.progress_bar, 4, 2, 1, 3)
        layout.addWidget(self.subtext_label, 5, 2, 1, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 9, 1)
        layout.addWidget(self.generate_button, 10, 3)
        layout.addWidget(self.close_button, 11, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 20, 1)

        self.generate_button.clicked.connect(self.go)
        self.lineedit.returnPressed.connect(self.go)
        self.copy_button.clicked.connect(self.on_copy_button_clicked)
        self.close_button.clicked.connect(self.close)

        self.reset()

    def on_got_code(self, code):
        self.code_label.setText(code)
        self.instructions_box.hide()
        if self.recipient:
            title = "{}'s invite code is:".format(self.recipient)
        else:
            title = "Your invite code is:"
        if sys.platform == 'darwin':
            self.code_box_title.setText(title)
            self.code_box_title.show()
        else:
            self.code_box.setTitle(title)
        self.code_box.show()
        self.waiting_label.hide()
        self.code_label.show()
        self.copy_button.show()
        self.subtext_label.show()
        self.subtext_label.setText(
            "This code will remain active only while this window is open and "
            "will expire immediately when used.")

    def on_got_introduction(self):
        self.code_box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(1)
        self.subtext_label.setText(
            "Connection established; sending credentials...")

    def on_send_completed(self):
        self.code_box.hide()
        self.progress_bar.show()
        self.progress_bar.setValue(2)
        self.close_button.setText("Finish")
        if self.recipient:
            text = "{}'s invitation to {} was accepted".format(
                    self.recipient, self.folder_name)
        else:
            text = "Your invitation to {} was accepted".format(
                    self.gateway.name)
        self.subtext_label.setText("Invite complete! {} at {}".format(
            text, datetime.now().strftime('%H:%M')))
        if get_preference('notifications', 'invite') != 'false':
            self.gui.show_message("Invite successful", text)

    def on_copy_button_clicked(self):
        code = self.code_label.text()
        for mode in get_clipboard_modes():
            set_clipboard_text(code, mode)
        self.subtext_label.setText("Copied '{}' to clipboard!".format(code))

    def reset(self):
        self.code_label.setText('')
        self.code_label.hide()
        self.copy_button.hide()
        self.code_box_title.hide()
        self.code_box.hide()
        self.close_button.hide()
        self.instructions_box.show()
        self.recipient = ''
        self.waiting_label.show()
        self.generate_button.show()

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
            self.reset()
            return
        else:
            msg.setWindowTitle(str(failure.type.__name__))
            msg.setText(str(failure.value))
        logging.error(str(failure))
        msg.exec_()
        self.reset()

    def go(self):
        if self.magic_folder_gateway:
            recipient = self.lineedit.text()
            if recipient:
                self.recipient = recipient
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Recipient required")
                msg.setText("Please enter a recipient name.")
                msg.exec_()
                return
        self.wormhole = Wormhole()
        self.wormhole.got_code.connect(self.on_got_code)
        self.wormhole.got_introduction.connect(self.on_got_introduction)
        self.wormhole.send_completed.connect(self.on_send_completed)
        self.instructions_box.hide()
        self.code_box.show()
        self.subtext_label.setText("This could take a few seconds...")
        self.generate_button.hide()
        self.close_button.show()
        self.settings = self.gateway.get_settings()
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
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
