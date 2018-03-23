# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QClipboard
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

if sys.platform == 'win32':
    from win32com.client import Dispatch  # pylint: disable=import-error

from gridsync import resource, settings, APP_NAME, autostart_file_path


@inlineCallbacks
def notify(systray, title, message, duration=5000):
    logging.debug(
        "Sending notification: title=%s message=%s", title, message)
    if sys.platform.startswith('linux'):
        from txdbus import client  # pylint: disable=import-error
        name = settings['application']['name']
        icon = resource(settings['application']['tray_icon'])
        try:
            conn = yield client.connect(reactor)
            robj = yield conn.getRemoteObject(
                'org.freedesktop.Notifications',
                '/org/freedesktop/Notifications')
            reply = yield robj.callRemote(
                'Notify', name, 0, icon, title, message, [], dict(), duration)
            logging.debug("Got reply: %s", reply)
            yield conn.disconnect()
        except Exception:  # pylint: disable=broad-except
            systray.showMessage(title, message, msecs=duration)
    else:
        systray.showMessage(title, message, msecs=duration)


def open_folder(path):
    path = os.path.expanduser(path)
    if sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    elif sys.platform == 'win32':
        os.startfile(path)
    else:
        subprocess.Popen(['xdg-open', path])


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
    logging.debug("Copied text '%s' to clipboard %i", text, mode)


def _autostart_enable_linux(executable):
    with open(autostart_file_path, 'w') as f:
        f.write('''\
[Desktop Entry]
Name={}
Comment={}
Type=Application
Exec=env PATH={} {}
Terminal=false
'''.format(APP_NAME, APP_NAME, os.environ['PATH'], executable))


def _autostart_enable_mac(executable):
    with open(autostart_file_path, 'w') as f:
        f.write('''\
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
'''.format(os.environ['PATH'], settings['build']['mac_bundle_identifier'],
           executable))


def _autostart_enable_windows(executable):
    shell = Dispatch('WScript.Shell')
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
    if getattr(sys, 'frozen', False):
        executable = os.path.realpath(sys.executable)
    else:
        executable = os.path.realpath(sys.argv[0])
    if sys.platform == 'win32':
        _autostart_enable_windows(executable)
    elif sys.platform == 'darwin':
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
