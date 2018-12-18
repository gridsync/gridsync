# -*- coding: utf-8 -*-

import os
from unittest.mock import MagicMock

import pytest
from twisted.internet.defer import CancelledError
from wormhole.errors import (
    LonelyError, ServerConnectionError, WelcomeError, WormholeError,
    WrongPasswordError)

from gridsync.errors import UpgradeRequiredError
from gridsync.invite import load_settings_from_cheatcode, is_valid_code
from gridsync.gui.invite import InviteCodeWidget, show_failure  # XXX


@pytest.mark.parametrize("code,result", [
    ['topmost-vagabond', False],  # Not three words
    ['corporate-cowbell-commando', False],  # First word not digit
    ['2-tanooki-travesty', False],  # Second word not in wordlist
    ['3-eating-wasabi', False],  # Third word not in wordlist
    ['1-cranky-tapeworm', True]
])
def test_is_valid_code(code, result):
    assert is_valid_code(code) == result


def test_load_settings_from_cheatcode(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir')
    providers_path = os.path.join(pkgdir, 'resources', 'providers')
    os.makedirs(providers_path)
    with open(os.path.join(providers_path, 'test-test.json'), 'w') as f:
        f.write('{"introducer": "pb://"}')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    settings = load_settings_from_cheatcode('test-test')
    assert settings['introducer'] == 'pb://'


def test_load_settings_from_cheatcode_none(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir-empty')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    assert load_settings_from_cheatcode('test-test') is None


def test_invite_code_widget_lineedit():
    w = InviteCodeWidget()
    assert w.lineedit


def test_invite_code_widget_tor_checkbox():
    w = InviteCodeWidget()
    assert w.tor_checkbox


@pytest.mark.parametrize("failure", [
    ServerConnectionError, WelcomeError, WrongPasswordError, LonelyError,
    UpgradeRequiredError, CancelledError, WormholeError])
def test_show_failure(failure, monkeypatch):
    monkeypatch.setattr('gridsync.gui.invite.QMessageBox', MagicMock())

    def fake_failure(failure):
        f = MagicMock()
        f.type = failure
        return f
    show_failure(fake_failure(failure))
