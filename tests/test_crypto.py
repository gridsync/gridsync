# -*- coding: utf-8 -*-

import sys

import nacl
import pytest

from gridsync.crypto import (
    Argon2iNotAvailableError, VersionError, encrypt, decrypt)

try:
    from nacl.pwhash import kdf_argon2i
    ARGON2I_AVAILABLE = True
except:
    ARGON2I_AVAILABLE = False


@pytest.fixture(scope='module')
def ciphertext():
    if nacl.__version__ == '1.1.2' and sys.version_info.major == 2:
        pytest.skip("Broken on PyNaCl version 1.1.2 under python2. "
                    "See: https://github.com/pyca/pynacl/issues/293")
    return encrypt(b'message', b'password')


@pytest.fixture(scope='module')
def ciphertext_with_scrypt():
    if nacl.__version__ == '1.1.2' and sys.version_info.major == 2:
        pytest.skip("Broken on PyNaCl version 1.1.2 under python2. "
                    "See: https://github.com/pyca/pynacl/issues/293")
    return encrypt(b'message', b'password', use_scrypt=True)


def test_scrypt_saltbytes():
    assert nacl.pwhash.SCRYPT_SALTBYTES == 32


def test_scryt_opslimit():
    assert nacl.pwhash.SCRYPT_OPSLIMIT_SENSITIVE == 33554432


def test_scrypt_memlimit():
    assert nacl.pwhash.SCRYPT_MEMLIMIT_SENSITIVE == 1073741824


def test_argon2i_saltbytes():
    if not ARGON2I_AVAILABLE:
        pytest.skip("Argon2i is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.ARGON2I_SALTBYTES == 16


def test_argon2i_opslimit():
    if not ARGON2I_AVAILABLE:
        pytest.skip("Argon2i is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.ARGON2I_OPSLIMIT_SENSITIVE == 8


def test_argon2i_memlimit():
    if not ARGON2I_AVAILABLE:
        pytest.skip("Argon2i is not available; PyNaCl may be out-of-date "
                    "(current version: {})".format(nacl.__version__))
    assert nacl.pwhash.ARGON2I_MEMLIMIT_SENSITIVE == 536870912


def test_secretbox_key_size():
    assert nacl.secret.SecretBox.KEY_SIZE == 32


def test_secretbox_nonce_size():
    assert nacl.secret.SecretBox.NONCE_SIZE == 24


@pytest.mark.slow
def test_decrypt_success(ciphertext):
    assert decrypt(ciphertext, b'password') == b'message'


@pytest.mark.slow
def test_decrypt_success_with_scrypt(ciphertext_with_scrypt):
    assert decrypt(ciphertext_with_scrypt, b'password') == b'message'


@pytest.mark.slow
def test_decrypt_fail_incorrect_password(ciphertext):
    with pytest.raises(nacl.exceptions.CryptoError):
        assert decrypt(ciphertext, b'password1') == b'message'


def test_decrypt_fail_argon2i_unavailable(monkeypatch):
    monkeypatch.setattr(
        "gridsync.crypto.ARGON2I_AVAILABLE", False, raising=True)
    with pytest.raises(Argon2iNotAvailableError):
        assert decrypt(b'2ciphertext', b'password') == b'message'


def test_decrypt_fail_incorrect_version_byte():
    with pytest.raises(VersionError):
        assert decrypt(b'3ciphertext', b'password') == b'message'
