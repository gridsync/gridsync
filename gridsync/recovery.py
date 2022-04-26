# -*- coding: utf-8 -*-

import json
import logging
import os
from pathlib import Path

from atomicwrites import atomic_write
from qtpy.QtCore import QObject, QPropertyAnimation, QThread, Signal
from qtpy.QtWidgets import QFileDialog, QMessageBox, QProgressDialog

from gridsync import APP_NAME
from gridsync.crypto import Crypter
from gridsync.gui.password import PasswordDialog
from gridsync.msg import error, question


class RecoveryKeyExporter(QObject):

    done = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.filepath = None
        self.progress = None
        self.animation = None
        self.crypter = None
        self.crypter_thread = None
        self.ciphertext = None

    def _on_encryption_failed(self, message):
        self.crypter_thread.quit()
        self.crypter_thread.wait()
        error(self.parent, "Error encrypting data", message)

    def _on_encryption_succeeded(self, ciphertext):
        self.crypter_thread.quit()
        self.crypter_thread.wait()
        if self.filepath:
            with atomic_write(self.filepath, mode="wb", overwrite=True) as f:
                f.write(ciphertext)
            self.done.emit(self.filepath)
            self.filepath = None
        else:
            self.ciphertext = ciphertext

    def _export_encrypted_recovery(self, gateway, password):
        settings = gateway.get_settings(include_secrets=True)
        if gateway.use_tor:
            settings["hide-ip"] = True
        data = json.dumps(settings)
        self.progress = QProgressDialog("Encrypting...", None, 0, 100)
        self.progress.show()
        self.animation = QPropertyAnimation(self.progress, b"value")
        self.animation.setDuration(6000)  # XXX
        self.animation.setStartValue(0)
        self.animation.setEndValue(99)
        self.animation.start()
        self.crypter = Crypter(data.encode(), password.encode())
        self.crypter_thread = QThread()
        self.crypter.moveToThread(self.crypter_thread)
        self.crypter.succeeded.connect(self.animation.stop)
        self.crypter.succeeded.connect(self.progress.close)
        self.crypter.succeeded.connect(self._on_encryption_succeeded)
        self.crypter.failed.connect(self.animation.stop)
        self.crypter.failed.connect(self.progress.close)
        self.crypter.failed.connect(self._on_encryption_failed)
        self.crypter_thread.started.connect(self.crypter.encrypt)
        self.crypter_thread.start()
        dest, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Select a destination",
            os.path.join(
                os.path.expanduser("~"),
                gateway.name + " Recovery Key.json.encrypted",
            ),
        )
        if not dest:
            return
        if self.ciphertext:
            with atomic_write(dest, mode="wb", overwrite=True) as f:
                f.write(self.ciphertext)
            self.done.emit(dest)
            self.ciphertext = None
        else:
            self.filepath = dest

    def _export_plaintext_recovery(self, gateway):
        dest, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Select a destination",
            os.path.join(
                os.path.expanduser("~"), gateway.name + " Recovery Key.json"
            ),
        )
        if not dest:
            return
        try:
            gateway.export(dest, include_secrets=True)
        except Exception as e:  # pylint: disable=broad-except
            error(self.parent, "Error creating Recovery Key", str(e))
            return
        self.done.emit(dest)

    def do_export(self, gateway):
        password, ok = PasswordDialog.get_password(
            label="Encryption passphrase (optional):",
            ok_button_text="Save Recovery Key...",
            help_text="A long passphrase will help keep your files safe in "
            "the event that your Recovery Key is ever compromised.",
            parent=self.parent,
        )
        if ok and password:
            self._export_encrypted_recovery(gateway, password)
        elif ok:
            self._export_plaintext_recovery(gateway)


class RecoveryKeyImporter(QObject):

    done = Signal(dict)

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.filepath = None
        self.progress = None
        self.animation = None
        self.crypter = None
        self.crypter_thread = None

    def _on_decryption_failed(self, msg):
        logging.error("%s", msg)
        self.crypter_thread.quit()
        self.crypter_thread.wait()
        if msg == "Decryption failed. Ciphertext failed verification":
            msg = "The provided passphrase was incorrect. Please try again."
        reply = QMessageBox.critical(
            self.parent,
            "Decryption Error",
            msg,
            QMessageBox.Abort | QMessageBox.Retry,
        )
        if reply == QMessageBox.Retry:
            self._load_from_file(self.filepath)

    def _on_decryption_succeeded(self, plaintext):
        logging.debug("Decryption of %s succeeded", self.filepath)
        self.crypter_thread.quit()
        self.crypter_thread.wait()
        try:
            settings = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError) as e:
            error(self, type(e).__name__, str(e))
            return
        if not isinstance(settings, dict):
            raise TypeError(f"settings must be 'dict'; got '{type(settings)}'")
        self.done.emit(settings)

    def _decrypt_content(self, data, password):
        logging.debug("Trying to decrypt %s...", self.filepath)
        self.progress = QProgressDialog(
            "Trying to decrypt {}...".format(os.path.basename(self.filepath)),
            None,
            0,
            100,
        )
        self.progress.show()
        self.animation = QPropertyAnimation(self.progress, b"value")
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
            settings = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.decoder.JSONDecodeError):
            logging.debug(
                "JSON decoding failed; %s is likely encrypted", self.filepath
            )
            password, ok = PasswordDialog.get_password(
                label="Decryption passphrase (required):",
                ok_button_text="Decrypt Recovery Key...",
                help_text="This Recovery Key is protected by a passphrase. "
                "Enter the correct passphrase to decrypt it.",
                show_stats=False,
                parent=self.parent,
            )
            if ok:
                self._decrypt_content(content, password)
            return
        if not isinstance(settings, dict):
            raise TypeError(f"settings must be 'dict'; got '{type(settings)}'")
        self.done.emit(settings)

    def _load_from_file(self, path):
        logging.debug("Loading %s...", self.filepath)
        try:
            with open(path, "rb") as f:
                content = f.read()
        except IsADirectoryError as err:
            error(
                self.parent,
                "Error loading Recovery Key",
                f"{path} is a directory, and not a valid Recovery Key."
                "\n\nPlease try again, selecting a valid Recovery Key file.",
                str(err),
            )
            return
        except Exception as e:  # pylint: disable=broad-except
            error(self.parent, "Error loading Recovery Key", str(e))
            return
        if not content:
            error(
                self.parent,
                "Invalid Recovery Key",
                f"The file {path} is empty."
                "\n\nPlease try again, selecting a valid Recovery Key file.",
            )
            return
        try:
            self._parse_content(content)
        except TypeError as err:
            error(
                self.parent,
                "Error parsing Recovery Key content",
                f"The file {path} does not appear to be a valid Recovery Key."
                "\n\nPlease try again, selecting a valid Recovery Key file.",
                str(err),
            )

    def _select_file(self):
        dialog = QFileDialog(self.parent, "Select a Recovery Key")
        dialog.setDirectory(os.path.expanduser("~"))
        dialog.setFileMode(QFileDialog.ExistingFile)
        if dialog.exec_():
            selected = dialog.selectedFiles()[0]
            if question(
                self.parent,
                f'Restore from "{Path(selected).name}"?',
                "By restoring from a Recovery Key, the configuration from "
                "the original device will be applied to this device -- "
                "including access to any previously-uploaded folders. Once "
                f"this process has completed, continuing to run {APP_NAME} "
                "on the original device can, in some circumstances, lead to "
                "data-loss. As a result, you should only restore from a "
                "Recovery Key in the event that the original device is no "
                f"longer running {APP_NAME}.\n\n"
                "Are you sure you wish to continue?",
            ):
                return selected
        return None

    def do_import(self, filepath=None):
        if not filepath:
            filepath = self._select_file()
        self.filepath = filepath
        if self.filepath:
            self._load_from_file(self.filepath)
