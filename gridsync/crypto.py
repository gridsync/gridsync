# -*- coding: utf-8 -*-

from nacl.exceptions import CryptoError
from nacl.pwhash import (
    kdf_scryptsalsa208sha256, SCRYPT_SALTBYTES, SCRYPT_OPSLIMIT_SENSITIVE,
    SCRYPT_MEMLIMIT_SENSITIVE)
from nacl.secret import SecretBox
from nacl.utils import random

try:
    from nacl.pwhash import (
        kdf_argon2id, ARGON2_SALTBYTES, ARGON2ID_OPSLIMIT_SENSITIVE,
        ARGON2ID_MEMLIMIT_SENSITIVE)
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False


class VersionError(CryptoError):
    pass


class Argon2NotAvailableError(VersionError):
    pass


def encrypt(message, password, use_scrypt=False):
    if ARGON2_AVAILABLE and not use_scrypt:
        version = b'2'
        salt = random(ARGON2_SALTBYTES)  # 16
        key = kdf_argon2id(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=ARGON2ID_OPSLIMIT_SENSITIVE,  # 4
            memlimit=ARGON2ID_MEMLIMIT_SENSITIVE   # 1073741824
        )
    else:
        version = b'1'
        salt = random(SCRYPT_SALTBYTES)  # 32
        key = kdf_scryptsalsa208sha256(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=SCRYPT_OPSLIMIT_SENSITIVE,  # 33554432
            memlimit=SCRYPT_MEMLIMIT_SENSITIVE   # 1073741824
        )
    box = SecretBox(key)
    encrypted = box.encrypt(message)
    return version + salt + encrypted


def decrypt(ciphertext, password):
    version = ciphertext[:1]
    ciphertext = ciphertext[1:]
    if version == b'2':
        if not ARGON2_AVAILABLE:
            raise Argon2NotAvailableError(
                "Argon2i is not available; PyNaCl may be out-of-date")
        salt = ciphertext[:ARGON2_SALTBYTES]  # 16
        encrypted = ciphertext[ARGON2_SALTBYTES:]
        key = kdf_argon2id(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=ARGON2ID_OPSLIMIT_SENSITIVE,  # 4
            memlimit=ARGON2ID_MEMLIMIT_SENSITIVE   # 1073741824
        )
    elif version == b'1':
        salt = ciphertext[:SCRYPT_SALTBYTES]  # 32
        encrypted = ciphertext[SCRYPT_SALTBYTES:]
        key = kdf_scryptsalsa208sha256(
            SecretBox.KEY_SIZE,  # 32
            password,
            salt,
            opslimit=SCRYPT_OPSLIMIT_SENSITIVE,  # 33554432
            memlimit=SCRYPT_MEMLIMIT_SENSITIVE   # 1073741824
        )
    else:
        raise VersionError("Invalid version byte; received {}".format(version))
    box = SecretBox(key)
    plaintext = box.decrypt(encrypted)
    return plaintext
