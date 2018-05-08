# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest

from gridsync.tor import get_tor


@pytest.inlineCallbacks
def test_get_tor(monkeypatch):
    fake_tor = MagicMock()
    monkeypatch.setattr('txtorcon.connect', lambda _: fake_tor)
    tor = yield get_tor(None)
    assert tor == fake_tor


@pytest.inlineCallbacks
def test_get_tor_return_none(monkeypatch):
    fake_connect = MagicMock(side_effect=RuntimeError())
    monkeypatch.setattr('txtorcon.connect', fake_connect)
    tor = yield get_tor(None)
    assert tor is None
