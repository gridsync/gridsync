# -*- coding: utf-8 -*-

import os
import webbrowser
from unittest.mock import MagicMock, Mock, call

import pytest

from gridsync.desktop import (
    _desktop_open,
    autostart_disable,
    autostart_enable,
    autostart_is_enabled,
    get_browser_name,
    get_clipboard_modes,
    get_clipboard_text,
    notify,
    open_enclosing_folder,
    open_path,
    set_clipboard_text,
)


def test_notify_calls__txdbus_notify_on_linux(monkeypatch):
    dbus_notify_args = [None, None, None]

    def fake_dbus_notify(title, message, duration):
        dbus_notify_args[0] = title
        dbus_notify_args[1] = message
        dbus_notify_args[2] = duration

    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("gridsync.desktop._txdbus_notify", fake_dbus_notify)
    notify(None, "test_title", "test_message", 9001)
    assert dbus_notify_args == ["test_title", "test_message", 9001]


@pytest.mark.parametrize("error", [OSError, RuntimeError])
def test_fallback_to_show_message_on_dbus_notify_error(error, monkeypatch):
    show_message_args = [None, None, None]

    def fake_show_message(title, message, msecs):
        show_message_args[0] = title
        show_message_args[1] = message
        show_message_args[2] = msecs

    fake_systray = MagicMock()
    fake_systray.showMessage = fake_show_message
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr(
        "gridsync.desktop._txdbus_notify", MagicMock(side_effect=error)
    )
    notify(fake_systray, "test_title", "test_message", 9001)
    assert show_message_args == ["test_title", "test_message", 9001]


def test_notify_call_systray_show_message(monkeypatch):
    show_message_args = [None, None, None]

    def fake_show_message(title, message, msecs):
        show_message_args[0] = title
        show_message_args[1] = message
        show_message_args[2] = msecs

    fake_systray = MagicMock()
    fake_systray.showMessage = fake_show_message
    monkeypatch.setattr("sys.platform", "win32")
    notify(fake_systray, "test_title", "test_message", 9001)
    assert show_message_args == ["test_title", "test_message", 9001]


def test__desktop_open_call_qdesktopservices_openurl(monkeypatch):
    fromlocalfile_mock = MagicMock()
    monkeypatch.setattr("qtpy.QtCore.QUrl.fromLocalFile", fromlocalfile_mock)
    openurl_mock = MagicMock()
    monkeypatch.setattr("qtpy.QtGui.QDesktopServices.openUrl", openurl_mock)
    _desktop_open("/test/path/file.txt")
    assert openurl_mock.call_count == 1 and fromlocalfile_mock.mock_calls == [
        call("/test/path/file.txt")
    ]


@pytest.mark.parametrize(
    "platform,mocked_call",
    [
        ("darwin", "subprocess.Popen"),
        ("win32", "subprocess.Popen"),
        ("linux", "gridsync.desktop._desktop_open"),
    ],
)
def test_open_enclosing_folder(platform, mocked_call, monkeypatch, tmp_path):
    m = MagicMock()
    monkeypatch.setattr(mocked_call, m)
    monkeypatch.setattr("sys.platform", platform)
    filepath = tmp_path / "file.txt"
    filepath.touch()
    open_enclosing_folder(filepath)
    call_args = m.mock_calls[0][1][0]
    if type(call_args) != str:
        call_args = " ".join(call_args)
    assert str(tmp_path) in call_args


def test_open_enclosing_folder_log_warn_if_not_exists(monkeypatch, tmp_path):
    m = MagicMock()
    monkeypatch.setattr("logging.warning", m)
    filepath = tmp_path / "file.txt"
    open_enclosing_folder(filepath)
    assert m.call_count > 0


@pytest.mark.parametrize(
    "platform,mocked_call",
    [
        ("darwin", "subprocess.Popen"),
        ("win32", "os.startfile"),
        ("linux", "gridsync.desktop._desktop_open"),
    ],
)
def test_open_path(platform, mocked_call, monkeypatch, tmp_path):
    m = MagicMock()
    monkeypatch.setattr(mocked_call, m, raising=False)
    monkeypatch.setattr("sys.platform", platform)
    filepath = tmp_path / "file.txt"
    filepath.touch()
    open_path(filepath)
    call_args = m.mock_calls[0][1][0]
    if type(call_args) != str:
        call_args = " ".join(call_args)
    assert str(tmp_path) in call_args


def test_open_path_log_warn_if_not_exists(monkeypatch, tmp_path):
    m = MagicMock()
    monkeypatch.setattr("logging.warning", m)
    filepath = tmp_path / "file.txt"
    open_path(filepath)
    assert m.call_count > 0


def test_get_clipboard_modes():
    assert len(get_clipboard_modes()) >= 1


@pytest.mark.skipif(
    "CI" in os.environ, reason="Fails on some headless environments"
)
def test_clipboard_text():
    set_clipboard_text("test")
    assert get_clipboard_text() == "test"


@pytest.fixture()
def tmpfile(tmpdir):
    return str(tmpdir.join("tmpfile.lnk"))  # .lnk extension required on win32


def test_autostart_is_enabled_true(tmpfile, monkeypatch):
    with open(tmpfile, "a"):
        os.utime(tmpfile, None)
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    assert autostart_is_enabled()


def test_autostart_is_enabled_false(tmpfile, monkeypatch):
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    assert not autostart_is_enabled()


def test_autostart_enable(tmpfile, monkeypatch):
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_appimage(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    appimage = "/test/gridsync.AppImage"
    monkeypatch.setattr("os.environ", {"PATH": "/tmp", "APPIMAGE": appimage})
    m = Mock()
    monkeypatch.setattr("gridsync.desktop._autostart_enable_linux", m)
    autostart_enable()
    assert m.call_args[0][0] == appimage


def test_autostart_enable_frozen(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_linux(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_mac(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    autostart_enable()
    assert autostart_is_enabled()


def test_autostart_enable_windows(tmpfile, monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setattr("gridsync.desktop.Dispatch", Mock(), raising=False)
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    autostart_enable()
    with open(tmpfile, "a"):
        os.utime(tmpfile, None)
    assert autostart_is_enabled()


def test_autostart_disable(tmpfile, monkeypatch):
    monkeypatch.setattr("gridsync.desktop.autostart_file_path", tmpfile)
    with open(tmpfile, "a"):
        os.utime(tmpfile, None)
    autostart_disable()
    assert not autostart_is_enabled()


@pytest.mark.parametrize(
    "mocked_name,result",
    [
        ("browser1", "Browser1"),
        ("test-browser", "Test Browser"),
        ("windows-default", "browser"),
        ("default", "browser"),
        ("", "browser"),
        ("xdg-open", "browser"),
    ],
)
def test_get_browser_name(monkeypatch, mocked_name, result):
    controller = Mock()
    controller.name = mocked_name
    monkeypatch.setattr("gridsync.desktop.webbrowser.get", lambda: controller)
    name = get_browser_name()
    assert name == result


@pytest.mark.parametrize("side_effect", [AttributeError, webbrowser.Error])
def test_get_browser_name_fallback_if_errors(monkeypatch, side_effect):
    monkeypatch.setattr(
        "gridsync.desktop.webbrowser.get", Mock(side_effect=side_effect)
    )
    name = get_browser_name()
    assert name == "browser"


def test_get_browser_name_fallback_if_get_returns_none(monkeypatch):
    monkeypatch.setattr("gridsync.desktop.webbrowser.get", lambda: None)
    name = get_browser_name()
    assert name == "browser"
