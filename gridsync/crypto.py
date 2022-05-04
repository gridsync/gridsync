# -*- coding: utf-8 -*-

import hashlib
import secrets
import string

from nacl.exceptions import CryptoError
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
from nacl.utils import random
from qtpy.QtCore import QObject, Signal

from gridsync.util import b58decode, b58encode


def randstr(length: int = 32, alphabet: str = "") -> str:
    if not alphabet:
        alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


def trunchash(s: str, length: int = 7) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:length]


class VersionError(CryptoError):
    pass


def encrypt(message: bytes, password: bytes) -> str:
    version = b"1"
    salt = random(argon2id.SALTBYTES)  # 16
    key = argon2id.kdf(
        SecretBox.KEY_SIZE,  # 32
        password,
        salt,
        opslimit=argon2id.OPSLIMIT_SENSITIVE,  # 4
        memlimit=argon2id.MEMLIMIT_SENSITIVE,  # 1073741824
    )
    box = SecretBox(key)
    encrypted = box.encrypt(message)
    return version + b58encode(salt + encrypted).encode()


def decrypt(ciphertext: bytes, password: bytes) -> bytes:
    version = ciphertext[:1]
    ciphertext = b58decode(ciphertext[1:].decode())
    if version == b"1":
        salt = ciphertext[: argon2id.SALTBYTES]  # 16
        encrypted = ciphertext[argon2id.SALTBYTES :]
        key = argon2id.kdf(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=argon2id.OPSLIMIT_SENSITIVE,  # 4
            memlimit=argon2id.MEMLIMIT_SENSITIVE,  # 1073741824
        )
    else:
        raise VersionError(
            "Invalid version byte; received {!r}".format(version)
        )
    box = SecretBox(key)
    plaintext = box.decrypt(encrypted)
    return plaintext


class Crypter(QObject):

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, data: bytes, password: bytes) -> None:
        super().__init__()
        self.data = data
        self.password = password

    def encrypt(self) -> None:
        try:
            self.succeeded.emit(encrypt(self.data, self.password))
        except Exception as err:  # pylint: disable=broad-except
            self.failed.emit(str(err))

    def decrypt(self) -> None:
        try:
            self.succeeded.emit(decrypt(self.data, self.password))
        except Exception as err:  # pylint: disable=broad-except
            self.failed.emit(str(err))
