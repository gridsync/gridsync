# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from PyQt5.QtWidgets import QMessageBox
import pytest
from pytest_twisted import inlineCallbacks

from gridsync.tor import tor_required, get_tor, get_tor_with_prompt


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
    monkeypatch.setattr(
        "gridsync.tor.settings", {"features": {"tor": "false"}}
    )
    tor = yield get_tor(None)
    assert tor is None


@inlineCallbacks
def test_get_tor_with_prompt_retry(monkeypatch):
    monkeypatch.setattr(
        "gridsync.tor.get_tor", MagicMock(side_effect=[None, "FakeTxtorcon"])
    )
    monkeypatch.setattr(
        "PyQt5.QtWidgets.QMessageBox.exec_",
        MagicMock(return_value=QMessageBox.Retry),
    )
    tor = yield get_tor_with_prompt(None)
    assert tor == "FakeTxtorcon"


@inlineCallbacks
def test_get_tor_with_prompt_abort(monkeypatch):
    monkeypatch.setattr("gridsync.tor.get_tor", MagicMock(return_value=None))
    monkeypatch.setattr(
        "PyQt5.QtWidgets.QMessageBox.exec_",
        MagicMock(return_value=QMessageBox.Abort),
    )
    tor = yield get_tor_with_prompt(None)
    assert tor is None
