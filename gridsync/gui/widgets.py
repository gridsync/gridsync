# -*- coding: utf-8 -*-

import json
import os

from PyQt5.QtCore import QPropertyAnimation, QThread
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPlainTextEdit, QProgressDialog, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync.crypto import Crypter
from gridsync.gui.password import PasswordDialog
from gridsync.msg import error
from gridsync.tor import get_tor


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

        self.maybe_enable_tor()

    @inlineCallbacks
    def maybe_enable_tor(self):
        tor = yield get_tor(reactor)
        if tor:
            self.mode_combobox.model().item(1).setEnabled(True)


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
        self.progress = None
        self.animation = None
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

        restore_selector_gbox = QGroupBox()
        restore_selector_gbox.setTitle("Import from Recovery Key:")
        restore_selector_gbox_layout = QGridLayout(restore_selector_gbox)
        restore_selector_gbox_layout.addWidget(self.restore_selector)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        layout = QGridLayout(self)
        layout.addWidget(connection_settings_gbox)
        layout.addWidget(encoding_parameters_gbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        #layout.addWidget(restore_selector_gbox)  # TODO: Remove related code
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
        settings = {
            'nickname': self.get_name(),
            'introducer': self.get_introducer(),
            'shares-total': self.get_shares_total(),
            'shares-needed': self.get_shares_needed(),
            'shares-happy': self.get_shares_happy(),
            'rootcap': self.rootcap  # Maybe this should be user-settable?
        }
        if self.connection_settings.mode_combobox.currentIndex() == 1:
            settings['hide-ip'] = True
        return settings

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
        self.progress = QProgressDialog("Trying to decrypt...", None, 0, 100)
        self.progress.show()
        self.animation = QPropertyAnimation(self.progress, b'value')
        self.animation.setDuration(5000)  # XXX
        self.animation.setStartValue(0)
        self.animation.setEndValue(99)
        self.animation.start()
        self.crypter = Crypter(data, password.encode())
        self.crypter_thread = QThread()
        self.crypter.moveToThread(self.crypter_thread)
        self.crypter.succeeded.connect(self.animation.stop)
        self.crypter.succeeded.connect(self.progress.close)
        self.crypter.succeeded.connect(self.on_decryption_succeeded)
        self.crypter.failed.connect(self.animation.stop)
        self.crypter.failed.connect(self.progress.close)
        self.crypter.failed.connect(self.on_decryption_failed)
        self.crypter_thread.started.connect(self.crypter.decrypt)
        self.crypter_thread.start()

    def parse_content(self, content):
        try:
            settings = json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            password, ok = PasswordDialog.get_password(
                self,
                "Decryption passphrase (required):",
                "This Recovery Key is protected by a passphrase. Enter the "
                "correct passphrase to decrypt it.",
                show_stats=False
            )
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
