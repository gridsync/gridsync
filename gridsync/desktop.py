# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys
import webbrowser

from atomicwrites import atomic_write
from qtpy.QtCore import QCoreApplication, QUrl
from qtpy.QtGui import QClipboard, QDesktopServices
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

if sys.platform == "win32":
    from win32com.client import Dispatch  # pylint: disable=import-error

from gridsync import APP_NAME, autostart_file_path, resource, settings


@inlineCallbacks
def _txdbus_notify(title, message, duration=5000):
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


def notify(systray, title, message, duration=5000):
    logging.debug("Sending desktop notification...")
    if sys.platform not in ("darwin", "win32"):
        try:
            _txdbus_notify(title, message, duration)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("%s; falling back to showMessage()...", str(exc))
            systray.showMessage(title, message, msecs=duration)
    else:
        systray.showMessage(title, message, msecs=duration)


def _desktop_open(path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def open_enclosing_folder(path):
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


def open_path(path):
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        logging.warning("Tried to open path that doesn't exist: %s", path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])  # pylint: disable=consider-using-with
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        _desktop_open(path)


def get_clipboard_modes():
    clipboard = QCoreApplication.instance().clipboard()
    modes = [QClipboard.Clipboard]
    if clipboard.supportsSelection():
        modes.append(QClipboard.Selection)
    if clipboard.supportsFindBuffer():
        modes.append(QClipboard.FindBuffer)
    return modes


def get_clipboard_text(mode=QClipboard.Clipboard):
    return QCoreApplication.instance().clipboard().text(mode)


def set_clipboard_text(text, mode=QClipboard.Clipboard):
    QCoreApplication.instance().clipboard().setText(text, mode)
    logging.debug(
        "Copied %i bytes to clipboard %i", len(text) if text else 0, mode
    )


def _autostart_enable_linux(executable):
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
def _autostart_enable_mac(executable):
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


def _autostart_enable_windows(executable):
    shell = Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(autostart_file_path)
    shortcut.Targetpath = executable
    shortcut.WorkingDirectory = os.path.dirname(executable)
    shortcut.save()


def autostart_enable():
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


def autostart_is_enabled():
    return os.path.exists(autostart_file_path)


def autostart_disable():
    logging.debug("Deleting autostart file '%s'...", autostart_file_path)
    os.remove(autostart_file_path)
    logging.debug("Deleted autostart file '%s'", autostart_file_path)


def get_browser_name() -> str:
    try:
        name = webbrowser.get().name
    except (AttributeError, webbrowser.Error):
        return "browser"
    if not name or name.endswith("default") or name == "xdg-open":
        return "browser"
    return name.replace("-", " ").title()
