# -*- coding: utf-8 -*-

import os
from unittest.mock import Mock

import pytest

from gridsync.desktop import (
    get_clipboard_modes, get_clipboard_text, set_clipboard_text,
    autostart_enable, autostart_is_enabled, autostart_disable)


@pytest.fixture()
def tmpfile(tmpdir):
    return str(tmpdir.join('tmpfile'))


def test_get_clipboard_modes():
    assert len(get_clipboard_modes()) >= 1


@pytest.mark.skipif(
    'CI' in os.environ, reason="Fails on some headless environments")
def test_clipboard_text():
    set_clipboard_text('test')
    assert get_clipboard_text() == 'test'


def test_autostart_is_enabled_true(tmpfile, monkeypatch):
    with open(tmpfile, 'a'):
        os.utime(tmpfile, None)
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    assert autostart_is_enabled()


def test_autostart_is_enabled_false(tmpfile, monkeypatch):
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    assert not autostart_is_enabled()


def test_autostart_enable(tmpfile, monkeypatch):
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_frozen(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_linux(tmpfile, monkeypatch):
    monkeypatch.setattr('sys.platform', 'linux')
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_mac(tmpfile, monkeypatch):
    monkeypatch.setattr('sys.platform', 'darwin')
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_windows(tmpfile, monkeypatch):
    monkeypatch.setattr('sys.platform', 'win32')
    monkeypatch.setattr('gridsync.desktop.Dispatch', Mock(), raising=False)
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    autostart_enable()
    with open(tmpfile, 'a'):
        os.utime(tmpfile, None)
    assert autostart_is_enabled()


def test_autostart_disable(tmpfile, monkeypatch):
    monkeypatch.setattr('gridsync.desktop.autostart_file_path', tmpfile)
    with open(tmpfile, 'a'):
        os.utime(tmpfile, None)
    autostart_disable()
    assert not autostart_is_enabled()
