# -*- coding: utf-8 -*-

from hashlib import sha256

import nacl
import pytest

from gridsync.crypto import Crypter, VersionError, decrypt, encrypt


def fast_kdf(*args, **kwargs):
    return sha256(args[1]).hexdigest()[:32].encode()


@pytest.fixture(scope="module")
def ciphertext_with_argon2():
    return encrypt(b"message", b"password")


@pytest.fixture(scope="module")
def crypter():
    return Crypter(b"data", b"password")


def test_argon2id_saltbytes():
    assert nacl.pwhash.argon2id.SALTBYTES == 16


def test_argon2id_opslimit():
    assert nacl.pwhash.argon2id.OPSLIMIT_SENSITIVE == 4


def test_argon2id_memlimit():
    assert nacl.pwhash.argon2id.MEMLIMIT_SENSITIVE == 1073741824


def test_secretbox_key_size():
    assert nacl.secret.SecretBox.KEY_SIZE == 32


def test_secretbox_nonce_size():
    assert nacl.secret.SecretBox.NONCE_SIZE == 24


def test_encrypt_decrypt_success_kdf_monkeypatch(monkeypatch):
    monkeypatch.setattr("nacl.pwhash.argon2id.kdf", fast_kdf)
    ciphertext = encrypt(b"message", b"password")
    assert decrypt(ciphertext, b"password") == b"message"


def test_encrypt_decrypt_fail_wrong_password_kdf_monkeypatch(monkeypatch):
    monkeypatch.setattr("nacl.pwhash.argon2id.kdf", fast_kdf)
    ciphertext = encrypt(b"message", b"password")
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext, b"hunter2") == b"message"


@pytest.mark.slow
def test_decrypt_success_slow(ciphertext_with_argon2):
    assert decrypt(ciphertext_with_argon2, b"password") == b"message"


@pytest.mark.slow
def test_decrypt_fail_incorrect_password_slow(ciphertext_with_argon2):
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext_with_argon2, b"password1") == b"message"


def test_decrypt_fail_incorrect_version_byte():
    with pytest.raises(VersionError):
        assert decrypt(b"2ciphertext", b"password") == b"message"


def test_crypter_encrypt_succeeded_signal(crypter, monkeypatch, qtbot):
    monkeypatch.setattr("gridsync.crypto.encrypt", lambda x, y: b"1ciphertext")
    with qtbot.wait_signal(crypter.succeeded):
        crypter.encrypt()


def test_crypter_encrypt_failed_signal(crypter, monkeypatch, qtbot):
    monkeypatch.delattr("gridsync.crypto.encrypt")
    with qtbot.wait_signal(crypter.failed):
        crypter.encrypt()


def test_crypter_decrypt_succeeded_signal(crypter, monkeypatch, qtbot):
    monkeypatch.setattr("gridsync.crypto.decrypt", lambda x, y: b"message")
    with qtbot.wait_signal(crypter.succeeded):
        crypter.decrypt()


def test_crypter_decrypt_failed_signal(crypter, monkeypatch, qtbot):
    monkeypatch.delattr("gridsync.crypto.decrypt")
    with qtbot.wait_signal(crypter.failed):
        crypter.decrypt()
