# -*- coding: utf-8 -*-

import os
from unittest.mock import Mock, MagicMock

import pytest

from gridsync.desktop import (
    _dbus_notify, notify, get_clipboard_modes, get_clipboard_text,
    set_clipboard_text, autostart_enable, autostart_is_enabled,
    autostart_disable)


def test__dbus_notify_bus_not_connected(monkeypatch):
    monkeypatch.setattr(
        'PyQt5.QtDBus.QDBusConnection.isConnected', lambda _: False)
    with pytest.raises(OSError):
        _dbus_notify('', '')


def test__dbus_notify_interface_error(monkeypatch):
    monkeypatch.setattr(
        'PyQt5.QtDBus.QDBusConnection.isConnected', lambda _: True)
    monkeypatch.setattr('PyQt5.QtDBus.QDBusInterface.lastError', MagicMock())
    with pytest.raises(RuntimeError):
        _dbus_notify('', '')


def test__dbus_notify_interface_called(monkeypatch):
    was_called = [False]

    def fake_call(*_):
        was_called[0] = True
    monkeypatch.setattr(
        'PyQt5.QtDBus.QDBusConnection.isConnected', lambda _: True)
    monkeypatch.setattr('PyQt5.QtDBus.QDBusInterface.isValid', lambda _: True)
    monkeypatch.setattr('PyQt5.QtDBus.QDBusInterface.call', fake_call)
    _dbus_notify('', '')
    assert was_called[0] is True


def test_notify_call__dbus_notify(monkeypatch):
    dbus_notify_args = [None, None, None]

    def fake_dbus_notify(title, message, duration):
        dbus_notify_args[0] = title
        dbus_notify_args[1] = message
        dbus_notify_args[2] = duration
    monkeypatch.setattr('sys.platform', 'linux')
    monkeypatch.setattr('gridsync.desktop._dbus_notify', fake_dbus_notify)
    notify(None, 'test_title', 'test_message', 9001)
    assert dbus_notify_args == ['test_title', 'test_message', 9001]


@pytest.mark.parametrize('error', [OSError, RuntimeError])
def test_notify_call__dbus_notify_fallback_on_error(error, monkeypatch):
    show_message_args = [None, None, None]

    def fake_show_message(title, message, msecs):
        show_message_args[0] = title
        show_message_args[1] = message
        show_message_args[2] = msecs
    fake_systray = MagicMock()
    fake_systray.showMessage = fake_show_message
    monkeypatch.setattr('sys.platform', 'linux')
    monkeypatch.setattr(
        'gridsync.desktop._dbus_notify', MagicMock(side_effect=error))
    notify(fake_systray, 'test_title', 'test_message', 9001)
    assert show_message_args == ['test_title', 'test_message', 9001]


def test_notify_call_systray_show_message(monkeypatch):
    show_message_args = [None, None, None]

    def fake_show_message(title, message, msecs):
        show_message_args[0] = title
        show_message_args[1] = message
        show_message_args[2] = msecs
    fake_systray = MagicMock()
    fake_systray.showMessage = fake_show_message
    monkeypatch.setattr('sys.platform', 'NOT_linux')
    notify(fake_systray, 'test_title', 'test_message', 9001)
    assert show_message_args == ['test_title', 'test_message', 9001]


@pytest.fixture()
def tmpfile(tmpdir):
    return str(tmpdir.join('tmpfile.lnk'))  # .lnk extension required on win32


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
