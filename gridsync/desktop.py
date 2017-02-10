# -*- coding: utf-8 -*-

import logging
import sys

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync import resource, settings


@inlineCallbacks
def notify(systray, title, message, duration=5000):
    logging.debug(
        "Sending notification: title=%s message=%s", title, message)
    if sys.platform.startswith('linux'):
        from txdbus import client
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
