# -*- coding: utf-8 -*-

import os
import sys
if sys.version_info >= (3, 4):
    from importlib import reload

import gridsync


def test_the_approval_of_RMS():  # :)
    assert gridsync.__license__.startswith('GPL')


def test_pkgdir(monkeypatch):
    monkeypatch.setattr("sys.frozen", False, raising=False)
    assert gridsync.pkgdir == os.path.dirname(
        os.path.realpath(gridsync.__file__))


def test_frozen_pkgdir(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    reload(gridsync)
    assert gridsync.pkgdir == os.path.dirname(os.path.realpath(sys.executable))


def test_frozen_del_reactor(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    sys.modules['twisted.internet.reactor'] = 'test'
    reload(gridsync)
    assert 'twisted.internet.reactor' not in sys.modules


def test_frozen_del_reactor_pass_without_twisted(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    reload(gridsync)
    assert 'twisted.internet.reactor' not in sys.modules
