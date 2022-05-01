# -*- coding: utf-8 -*-

from collections import namedtuple
from unittest.mock import MagicMock

import pytest
from pytest_twisted import inlineCallbacks
from qtpy.QtWidgets import QMessageBox

from gridsync.tor import get_tor, get_tor_with_prompt, tor_required


@pytest.mark.parametrize(
    "furl,result",
    [
        [None, False],  # Empty fURL; AttributeError
        ["test", False],  # Invalid fURL; IndexError
        ["pb://a@example.org:9999/b", False],  # No .onion addrs
        ["pb://a@test.onion:9999/b", True],  # Only .onion addr
        [
            "pb://a@example.org:9999,test.onion:9999/b",
            False,
        ],  # Clearnet available
        [
            "pb://a@example.onion:9999,test.onion:9999/b",
            True,
        ],  # Only .onion addrs
    ],
)
def test_tor_required(furl, result):
    assert tor_required(furl) == result


@inlineCallbacks
def test_get_tor(monkeypatch):
    f = namedtuple("Features", "tor")
    monkeypatch.setattr("gridsync.tor.features", f(tor=True))
    fake_tor = MagicMock()
    monkeypatch.setattr("txtorcon.connect", lambda _: fake_tor)
    tor = yield get_tor(None)
    assert tor == fake_tor


@inlineCallbacks
def test_get_tor_return_none(monkeypatch):
    fake_connect = MagicMock(side_effect=RuntimeError())
    monkeypatch.setattr("txtorcon.connect", fake_connect)
    tor = yield get_tor(None)
    assert tor is None


@inlineCallbacks
def test_get_tor_return_none_feature_disabled(monkeypatch):
    f = namedtuple("Features", "tor")
    monkeypatch.setattr("gridsync.tor.features", f(tor=False))
    tor = yield get_tor(None)
    assert tor is None


@inlineCallbacks
def test_get_tor_with_prompt_retry(monkeypatch):
    monkeypatch.setattr(
        "gridsync.tor.get_tor", MagicMock(side_effect=[None, "FakeTxtorcon"])
    )
    monkeypatch.setattr(
        "qtpy.QtWidgets.QMessageBox.exec_",
        MagicMock(return_value=QMessageBox.Retry),
    )
    tor = yield get_tor_with_prompt(None)
    assert tor == "FakeTxtorcon"


@inlineCallbacks
def test_get_tor_with_prompt_abort(monkeypatch):
    monkeypatch.setattr("gridsync.tor.get_tor", MagicMock(return_value=None))
    monkeypatch.setattr(
        "qtpy.QtWidgets.QMessageBox.exec_",
        MagicMock(return_value=QMessageBox.Abort),
    )
    tor = yield get_tor_with_prompt(None)
    assert tor is None
