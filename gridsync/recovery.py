# -*- coding: utf-8 -*-

import json
import logging
import os

from PyQt5.QtCore import pyqtSignal, QObject, QPropertyAnimation, QThread
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from gridsync.crypto import Crypter
from gridsync.gui.password import PasswordDialog
from gridsync.msg import error


class RecoveryKeyImporter(QObject):

    done = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(RecoveryKeyImporter, self).__init__()
        self.parent = parent
        self.filepath = None
        self.progress = None
        self.animation = None
        self.crypter = None
        self.crypter_thread = None

    def _on_decryption_failed(self, msg):
        logging.error("%s", msg)
        self.crypter_thread.quit()
        if msg == "Decryption failed. Ciphertext failed verification":
            msg = "The provided passphrase was incorrect. Please try again."
        reply = QMessageBox.critical(
            self.parent,
            "Decryption Error",
            msg,
            QMessageBox.Abort | QMessageBox.Retry
        )
        self.crypter_thread.wait()
        if reply == QMessageBox.Retry:
            self._load_from_file(self.filepath)

    def _on_decryption_succeeded(self, plaintext):
        logging.debug("Decryption of %s succeeded", self.filepath)
        self.crypter_thread.quit()
        try:
            settings = json.loads(plaintext.decode('utf-8'))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError) as e:
            error(self, type(e).__name__, str(e))
            return
        self.done.emit(settings)
        self.crypter_thread.wait()

    def _decrypt_content(self, data, password):
        logging.debug("Trying to decrypt %s...", self.filepath)
        self.progress = QProgressDialog(
            "Trying to decrypt {}...".format(os.path.basename(self.filepath)),
            None,
            0,
            100
        )
        self.progress.show()
        self.animation = QPropertyAnimation(self.progress, b'value')
        self.animation.setDuration(6000)  # XXX
        self.animation.setStartValue(0)
        self.animation.setEndValue(99)
        self.animation.start()
        self.crypter = Crypter(data, password.encode())
        self.crypter_thread = QThread()
        self.crypter.moveToThread(self.crypter_thread)
        self.crypter.succeeded.connect(self.animation.stop)
        self.crypter.succeeded.connect(self.progress.close)
        self.crypter.succeeded.connect(self._on_decryption_succeeded)
        self.crypter.failed.connect(self.animation.stop)
        self.crypter.failed.connect(self.progress.close)
        self.crypter.failed.connect(self._on_decryption_failed)
        self.crypter_thread.started.connect(self.crypter.decrypt)
        self.crypter_thread.start()

    def _parse_content(self, content):
        try:
            settings = json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            logging.debug(
                "JSON decoding failed; %s is likely encrypted", self.filepath)
            password, ok = PasswordDialog.get_password(
                self.parent,
                "Decryption passphrase (required):",
                "This Recovery Key is protected by a passphrase. Enter the "
                "correct passphrase to decrypt it.",
                show_stats=False
            )
            if ok:
                self._decrypt_content(content, password)
            return
        self.done.emit(settings)

    def _load_from_file(self, path):
        logging.debug("Loading %s...", self.filepath)
        try:
            with open(path, 'rb') as f:
                content = f.read()
        except Exception as e:  # pylint: disable=broad-except
            error(self, type(e).__name__, str(e))
            return
        self._parse_content(content)

    def _select_file(self):
        dialog = QFileDialog(self.parent, "Select a Recovery Key")
        dialog.setDirectory(os.path.expanduser('~'))
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_():
            return dialog.selectedFiles()[0]
        return None

    def do_import(self, filepath=None):
        if not filepath:
            filepath = self._select_file()
        self.filepath = filepath
        if self.filepath:
            self._load_from_file(self.filepath)
