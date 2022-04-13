# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest
from twisted.internet.defer import CancelledError
from wormhole.errors import (
    LonelyError,
    ServerConnectionError,
    WelcomeError,
    WormholeError,
    WrongPasswordError,
)

from gridsync.errors import UpgradeRequiredError
from gridsync.gui.invite import InviteCodeWidget, show_failure  # XXX
from gridsync.invite import is_valid_code


@pytest.mark.parametrize(
    "code,result",
    [
        ["topmost-vagabond", False],  # Not three words
        ["corporate-cowbell-commando", False],  # First word not digit
        ["2-tanooki-travesty", False],  # Second word not in wordlist
        ["3-eating-wasabi", False],  # Third word not in wordlist
        ["0-almighty-aardvark", False],  # Non-existent "cheat code"
        ["1-cranky-tapeworm", True],
    ],
)
def test_is_valid_code(code, result):
    assert is_valid_code(code) == result


def test_invite_code_widget_lineedit():
    w = InviteCodeWidget()
    assert w.lineedit


def test_invite_code_widget_tor_checkbox():
    w = InviteCodeWidget()
    assert w.tor_checkbox


@pytest.mark.parametrize(
    "failure",
    [
        ServerConnectionError,
        WelcomeError,
        WrongPasswordError,
        LonelyError,
        UpgradeRequiredError,
        CancelledError,
        WormholeError,
    ],
)
def test_show_failure(failure, monkeypatch):
    monkeypatch.setattr("gridsync.gui.invite.QMessageBox", MagicMock())

    def fake_failure(failure):
        f = MagicMock()
        f.type = failure
        return f

    show_failure(fake_failure(failure))
