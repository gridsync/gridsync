# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest

from gridsync.tor import tor_required, get_tor


@pytest.mark.parametrize("furl,result", [
    [None, False],  # Empty fURL; AttributeError
    ['test', False],  # Invalid fURL; IndexError
    ['pb://a@example.org:9999/b', False],  # No .onion addrs
    ['pb://a@test.onion:9999/b', True],  # Only .onion addr
    ['pb://a@example.org:9999,test.onion:9999/b', False],  # Clearnet available
    ['pb://a@example.onion:9999,test.onion:9999/b', True],  # Only .onion addrs
])
def test_tor_required(furl, result):
    assert tor_required(furl) == result


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
