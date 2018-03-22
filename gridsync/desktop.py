# -*- coding: utf-8 -*-

import logging
import os
import subprocess
import sys

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QClipboard
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync import resource, settings, APP_NAME


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


def _autostart_enable_linux():
    desktop_file_path = os.path.join(
        os.environ.get(
            'XDG_CONFIG_HOME',
            os.path.join(os.path.expanduser('~'), '.config')
        ),
        'autostart',
        APP_NAME + '.desktop'
    )
    logging.debug("Writing autostart file to '%s'...", desktop_file_path)
    if getattr(sys, 'frozen', False):
        executable = sys.executable
    else:
        executable = sys.argv[0]
    desktop_file_contents = '''[Desktop Entry]
Name={}
Comment={}
Type=Application
Exec=env PATH={} {}
'''.format(APP_NAME, APP_NAME, os.environ['PATH'], executable)
    try:
        os.makedirs(os.path.dirname(desktop_file_path))
    except OSError:
        pass
    with open(desktop_file_path, 'w') as f:
        f.write(desktop_file_contents)
    logging.debug("Wrote autostart file to %s", desktop_file_path)
    logging.debug(desktop_file_contents)


def _autostart_enabled_linux():
    desktop_file_path = os.path.join(
        os.environ.get(
            'XDG_CONFIG_HOME',
            os.path.join(os.path.expanduser('~'), '.config')
        ),
        'autostart',
        APP_NAME + '.desktop'
    )
    if os.path.exists(desktop_file_path):
        return True
    return False


def _autostart_disable_linux():
    desktop_file_path = os.path.join(
        os.environ.get(
            'XDG_CONFIG_HOME',
            os.path.join(os.path.expanduser('~'), '.config')
        ),
        'autostart',
        APP_NAME + '.desktop'
    )
    logging.debug("Deleting autostart file '%s'...", desktop_file_path)
    os.remove(desktop_file_path)
    logging.debug("Deleted autostart file '%s'", desktop_file_path)


def _autostart_enable_mac():
    plist_file_path = os.path.join(
        os.path.expanduser('~'), 'Library', 'LaunchAgents', APP_NAME + '.plist'
    )
    if getattr(sys, 'frozen', False):
        executable = sys.executable
    else:
        executable = sys.argv[0]
    plist_file_contents = '''\
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
           executable)
    try:
        os.makedirs(os.path.dirname(plist_file_path))
    except OSError:
        pass
    with open(plist_file_path, 'w') as f:
        f.write(plist_file_contents)


def _autostart_enabled_mac():
    plist_file_path = os.path.join(
        os.path.expanduser('~'), 'Library', 'LaunchAgents', APP_NAME + '.plist'
    )
    if os.path.exists(plist_file_path):
        return True
    return False


def _autostart_disable_mac():
    plist_file_path = os.path.join(
        os.path.expanduser('~'), 'Library', 'LaunchAgents', APP_NAME + '.plist'
    )
    logging.debug("Deleting autostart file '%s'...", plist_file_path)
    os.remove(plist_file_path)
    logging.debug("Deleted autostart file '%s'", plist_file_path)


def autostart_enable():
    if sys.platform.startswith('linux'):
        _autostart_enable_linux()
    elif sys.platform == 'darwin':
        _autostart_enable_mac()


def autostart_enabled():
    if sys.platform.startswith('linux'):
        return _autostart_enabled_linux()
    elif sys.platform == 'darwin':
        return _autostart_enabled_mac()


def autostart_disable():
    if sys.platform.startswith('linux'):
        _autostart_disable_linux()
    elif sys.platform == 'darwin':
        _autostart_disable_mac()
