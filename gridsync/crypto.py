# -*- coding: utf-8 -*-

import datetime
import hashlib
import secrets
import string

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from nacl.exceptions import CryptoError
from nacl.pwhash import argon2id
from nacl.secret import SecretBox
from nacl.utils import random
from PyQt5.QtCore import QObject, pyqtSignal

from gridsync.util import b58decode, b58encode


def randstr(length: int = 32, alphabet: str = "") -> str:
    if not alphabet:
        alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


def trunchash(s, length=7):
    return hashlib.sha256(s.encode()).hexdigest()[:length]


def create_certificate(pemfile: str, common_name: str) -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    subject = issuer = x509.Name(
        [x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name)]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365 * 100)
        )
        .sign(key, hashes.SHA256())
    )
    with open(pemfile, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
            + cert.public_bytes(serialization.Encoding.PEM)
        )
    return cert.fingerprint(hashes.SHA256())


def get_certificate_digest(pemfile: str) -> bytes:
    with open(pemfile) as f:
        cert = x509.load_pem_x509_certificate(f.read().encode())
    digest = cert.fingerprint(hashes.SHA256())
    return digest


def get_certificate_public_bytes(pemfile: str) -> bytes:
    with open(pemfile) as f:
        cert = x509.load_pem_x509_certificate(f.read().encode())
    public_bytes = cert.public_bytes(serialization.Encoding.PEM)
    return public_bytes


class VersionError(CryptoError):
    pass


def encrypt(message, password):
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


def decrypt(ciphertext, password):
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
        raise VersionError("Invalid version byte; received {}".format(version))
    box = SecretBox(key)
    plaintext = box.decrypt(encrypted)
    return plaintext


class Crypter(QObject):

    succeeded = pyqtSignal(object)  # bytes (python3) or str (python2)
    failed = pyqtSignal(str)

    def __init__(self, data, password):
        super().__init__()
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
