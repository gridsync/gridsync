# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import subprocess
import sys
import webbrowser
from typing import TYPE_CHECKING

from atomicwrites import atomic_write
from qtpy.QtCore import QUrl
from qtpy.QtGui import QClipboard, QDesktopServices
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

if sys.platform == "win32":
    from win32com.client import Dispatch  # pylint: disable=import-error

from gridsync import APP_NAME, autostart_file_path, resource, settings

if TYPE_CHECKING:
    from typing import Optional

    from qtpy.QtWidgets import QSystemTrayIcon

    from gridsync.types_ import TwistedDeferred


@inlineCallbacks
def _txdbus_notify(
    title: str, message: str, duration: int = 5000
) -> TwistedDeferred[None]:
    from txdbus import client  # pylint: disable=import-error

    conn = yield client.connect(reactor)
    robj = yield conn.getRemoteObject(
        "org.freedesktop.Notifications", "/org/freedesktop/Notifications"
    )
    # See https://developer.gnome.org/notification-spec/
    reply = yield robj.callRemote(
        "Notify",
        APP_NAME,
        0,  # 0 means don't replace existing notifications.
        resource(settings["application"]["tray_icon"]),
        title,
        message,
        [],
        {},
        duration,
    )
    logging.debug("Got reply from DBus: %s", reply)
    yield conn.disconnect()


@inlineCallbacks
def notify(
    systray: QSystemTrayIcon, title: str, message: str, duration: int = 5000
) -> TwistedDeferred[None]:
    logging.debug("Sending desktop notification...")
    if sys.platform not in ("darwin", "win32"):
        try:
            yield _txdbus_notify(title, message, duration)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("%s; falling back to showMessage()...", str(exc))
            if systray and systray.supportsMessages():
                systray.showMessage(title, message, msecs=duration)
            else:
                logging.info("%s: %s", title, message)
    elif systray and systray.supportsMessages():
        systray.showMessage(title, message, msecs=duration)
    else:
        logging.info("%s: %s", title, message)


def _desktop_open(path: str) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def open_enclosing_folder(path: str) -> None:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        logging.warning("Tried to open path that doesn't exist: %s", path)
    elif sys.platform == "darwin":
        subprocess.Popen(  # pylint: disable=consider-using-with
            ["open", "--reveal", path]
        )
    elif sys.platform == "win32":
        subprocess.Popen(  # pylint: disable=consider-using-with
            'explorer /select,"{}"'.format(path)
        )
    else:
        # TODO: Get file-manager via `xdg-mime query default inode/directory`
        # and, if 'org.gnome.Nautilus.desktop', call `nautilus --select`?
        _desktop_open(os.path.dirname(path))


def open_path(path: str) -> None:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        logging.warning("Tried to open path that doesn't exist: %s", path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])  # pylint: disable=consider-using-with
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        _desktop_open(path)


def _get_clipboard() -> Optional[QClipboard]:
    from qtpy.QtGui import QGuiApplication
    from qtpy.QtWidgets import QApplication

    qapp = QApplication.instance()
    if isinstance(qapp, (QApplication, QGuiApplication)):
        return qapp.clipboard()
    return None


def get_clipboard_modes() -> list:
    modes = [QClipboard.Clipboard]
    clipboard = _get_clipboard()
    if not clipboard:
        return modes
    if clipboard.supportsSelection():
        modes.append(QClipboard.Selection)
    if clipboard.supportsFindBuffer():
        modes.append(QClipboard.FindBuffer)
    return modes


def get_clipboard_text(
    mode: QClipboard.Mode = QClipboard.Clipboard,
) -> Optional[str]:
    clipboard = _get_clipboard()
    if not clipboard:
        return None
    return clipboard.text(mode)


def set_clipboard_text(
    text: str, mode: QClipboard.Mode = QClipboard.Clipboard
) -> None:
    clipboard = _get_clipboard()
    if not clipboard:
        logging.warning("Clipboard not available")
        return
    clipboard.setText(text, mode)
    logging.debug(
        "Copied %i bytes to clipboard %s", len(text) if text else 0, str(mode)
    )


def _autostart_enable_linux(executable: str) -> None:
    with atomic_write(autostart_file_path, mode="w", overwrite=True) as f:
        f.write(
            """\
[Desktop Entry]
Name={0}
Comment={0}
Type=Application
Exec=env PATH={1} {2}
Terminal=false
""".format(
                APP_NAME, os.environ["PATH"], executable
            )
        )


# pylint: disable=line-too-long
def _autostart_enable_mac(executable: str) -> None:
    with atomic_write(autostart_file_path, mode="w", overwrite=True) as f:
        f.write(
            """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>{}</string>
    </dict>
    <key>Label</key>
    <string>{}</string>
    <key>Program</key>
    <string>{}</string>
    <key>RunAtLoad</key>
    <true/>
  </dict>
</plist>
""".format(
                os.environ["PATH"],
                settings["build"]["mac_bundle_identifier"],
                executable,
            )
        )


def _autostart_enable_windows(executable: str) -> None:
    if sys.platform == "win32":
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(autostart_file_path)
        shortcut.Targetpath = executable
        shortcut.WorkingDirectory = os.path.dirname(executable)
        shortcut.save()


def autostart_enable() -> None:
    logging.debug("Writing autostart file to '%s'...", autostart_file_path)
    try:
        os.makedirs(os.path.dirname(autostart_file_path))
    except OSError:
        pass
    appimage_path = os.environ.get("APPIMAGE")
    frozen = getattr(sys, "frozen", False)
    if frozen and frozen == "macosx_app":  # py2app
        executable = os.path.join(
            os.path.dirname(os.path.realpath(sys.executable)), APP_NAME
        )
    elif appimage_path:
        executable = appimage_path
    elif frozen:
        executable = os.path.realpath(sys.executable)
    else:
        executable = os.path.realpath(sys.argv[0])
    if sys.platform == "win32":
        _autostart_enable_windows(executable)
    elif sys.platform == "darwin":
        _autostart_enable_mac(executable)
    else:
        _autostart_enable_linux(executable)
    logging.debug("Wrote autostart file to '%s'", autostart_file_path)


def autostart_is_enabled() -> bool:
    return os.path.exists(autostart_file_path)


def autostart_disable() -> None:
    logging.debug("Deleting autostart file '%s'...", autostart_file_path)
    try:
        os.remove(autostart_file_path)
    except FileNotFoundError:
        logging.warning("Tried to remove autostart file that did not exist.")
        return
    logging.debug("Deleted autostart file '%s'", autostart_file_path)


def get_browser_name() -> str:
    try:
        name = webbrowser.get().name
    except (AttributeError, webbrowser.Error):
        return "browser"
    if not name or name.endswith("default") or name == "xdg-open":
        return "browser"
    return name.replace("-", " ").title()
