# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal, QObject
from nacl.exceptions import CryptoError
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
from nacl.utils import random

from gridsync.util import b58encode, b58decode


class VersionError(CryptoError):
    pass


def encrypt(message, password):
    version = b'1'
    salt = random(argon2id.SALTBYTES)  # 16
    key = argon2id.kdf(
        SecretBox.KEY_SIZE,  # 32
        password,
        salt,
        opslimit=argon2id.OPSLIMIT_SENSITIVE,  # 4
        memlimit=argon2id.MEMLIMIT_SENSITIVE   # 1073741824
    )
    box = SecretBox(key)
    encrypted = box.encrypt(message)
    return version + b58encode(salt + encrypted).encode()


def decrypt(ciphertext, password):
    version = ciphertext[:1]
    ciphertext = b58decode(ciphertext[1:].decode())
    if version == b'1':
        salt = ciphertext[:argon2id.SALTBYTES]  # 16
        encrypted = ciphertext[argon2id.SALTBYTES:]
        key = argon2id.kdf(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=argon2id.OPSLIMIT_SENSITIVE,  # 4
            memlimit=argon2id.MEMLIMIT_SENSITIVE   # 1073741824
        )
    else:
        raise VersionError("Invalid version byte; received {}".format(version))
    box = SecretBox(key)
    plaintext = box.decrypt(encrypted)
    return plaintext


class Crypter(QObject):

    succeeded = pyqtSignal(object)  # bytes (python3) or str (python2)
    failed = pyqtSignal(str)

    def __init__(self, data, password):
        super(Crypter, self).__init__()
        self.data = data
        self.password = password

    def encrypt(self):
        try:
            self.succeeded.emit(encrypt(self.data, self.password))
        except Exception as err:  # pylint: disable=broad-except
            self.failed.emit(str(err))

    def decrypt(self):
        try:
            self.succeeded.emit(decrypt(self.data, self.password))
        except Exception as err:  # pylint: disable=broad-except
            self.failed.emit(str(err))
