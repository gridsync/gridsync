# -*- coding: utf-8 -*-

from hashlib import sha256
import sys

import nacl
import pytest

import gridsync
from gridsync.crypto import (
    ARGON2_AVAILABLE, Argon2NotAvailableError, VersionError, encrypt, decrypt,
    Crypter)


def fast_kdf(*args, **kwargs):
    return sha256(args[1]).hexdigest()[:32].encode()


@pytest.fixture(scope='module')
def ciphertext_with_argon2():
    if nacl.__version__ == '1.1.2' and sys.version_info.major == 2:
        pytest.skip("Broken on PyNaCl version 1.1.2 under python2. "
                    "See: https://github.com/pyca/pynacl/issues/293")
    return encrypt(b'message', b'password', use_scrypt=False)


@pytest.fixture(scope='module')
def ciphertext_with_scrypt():
    if nacl.__version__ == '1.1.2' and sys.version_info.major == 2:
        pytest.skip("Broken on PyNaCl version 1.1.2 under python2. "
                    "See: https://github.com/pyca/pynacl/issues/293")
    return encrypt(b'message', b'password', use_scrypt=True)


@pytest.fixture(scope='module')
def crypter():
    return Crypter(b'data', b'password')


def test_scrypt_saltbytes():
    assert nacl.pwhash.SCRYPT_SALTBYTES == 32


def test_scrypt_opslimit():
    assert nacl.pwhash.SCRYPT_OPSLIMIT_SENSITIVE == 33554432


def test_scrypt_memlimit():
    assert nacl.pwhash.SCRYPT_MEMLIMIT_SENSITIVE == 1073741824


def test_argon2_saltbytes():
    if not ARGON2_AVAILABLE:
        pytest.skip("Argon2id is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.argon2id.SALTBYTES == 16


def test_argon2id_opslimit():
    if not ARGON2_AVAILABLE:
        pytest.skip("Argon2id is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.argon2id.OPSLIMIT_SENSITIVE == 4


def test_argon2id_memlimit():
    if not ARGON2_AVAILABLE:
        pytest.skip("Argon2id is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.argon2id.MEMLIMIT_SENSITIVE == 1073741824


def test_secretbox_key_size():
    assert nacl.secret.SecretBox.KEY_SIZE == 32


def test_secretbox_nonce_size():
    assert nacl.secret.SecretBox.NONCE_SIZE == 24


def test_encrypt_decrypt_success_argon2_monkeypatch(monkeypatch):
    if not ARGON2_AVAILABLE:
        pytest.skip("Argon2id is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    monkeypatch.setattr('gridsync.crypto.argon2id.kdf', fast_kdf)
    ciphertext = encrypt(b'message', b'password')
    assert decrypt(ciphertext, b'password') == b'message'


def test_encrypt_decrypt_fail_wrong_password_argon2_monkeypatch(monkeypatch):
    if not ARGON2_AVAILABLE:
        pytest.skip("Argon2id is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    monkeypatch.setattr('gridsync.crypto.argon2id.kdf', fast_kdf)
    ciphertext = encrypt(b'message', b'password')
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext, b'hunter2') == b'message'


def test_encrypt_decrypt_success_scrypt_monkeypatch(monkeypatch):
    monkeypatch.setattr('gridsync.crypto.kdf_scryptsalsa208sha256', fast_kdf)
    ciphertext = encrypt(b'message', b'password', use_scrypt=True)
    assert decrypt(ciphertext, b'password') == b'message'


def test_encrypt_decrypt_fail_wrong_password_scrypt_monkeypatch(monkeypatch):
    monkeypatch.setattr('gridsync.crypto.kdf_scryptsalsa208sha256', fast_kdf)
    ciphertext = encrypt(b'message', b'password', use_scrypt=True)
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext, b'hunter2') == b'message'


@pytest.mark.slow
def test_decrypt_success_slow(ciphertext_with_argon2):
    assert decrypt(ciphertext_with_argon2, b'password') == b'message'


@pytest.mark.slow
def test_decrypt_success_with_scrypt_slow(ciphertext_with_scrypt):
    assert decrypt(ciphertext_with_scrypt, b'password') == b'message'


@pytest.mark.slow
def test_decrypt_fail_incorrect_password_slow(ciphertext_with_argon2):
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext_with_argon2, b'password1') == b'message'


def test_decrypt_fail_argon2id_unavailable(monkeypatch):
    monkeypatch.setattr(
        "gridsync.crypto.ARGON2_AVAILABLE", False, raising=True)
    with pytest.raises(Argon2NotAvailableError):
        assert decrypt(b'2ciphertext', b'password') == b'message'


def test_decrypt_fail_incorrect_version_byte():
    with pytest.raises(VersionError):
        assert decrypt(b'3ciphertext', b'password') == b'message'


def test_crypter_encrypt_succeeded_signal(crypter, monkeypatch, qtbot):
    monkeypatch.setattr('gridsync.crypto.encrypt', lambda x, y: b'1ciphertext')
    with qtbot.wait_signal(crypter.succeeded):
        crypter.encrypt()


def test_crypter_encrypt_failed_signal(crypter, monkeypatch, qtbot):
    monkeypatch.delattr('gridsync.crypto.encrypt')
    with qtbot.wait_signal(crypter.failed):
        crypter.encrypt()


def test_crypter_decrypt_succeeded_signal(crypter, monkeypatch, qtbot):
    monkeypatch.setattr('gridsync.crypto.decrypt', lambda x, y: b'message')
    with qtbot.wait_signal(crypter.succeeded):
        crypter.decrypt()


def test_crypter_decrypt_failed_signal(crypter, monkeypatch, qtbot):
    monkeypatch.delattr('gridsync.crypto.decrypt')
    with qtbot.wait_signal(crypter.failed):
        crypter.decrypt()
