# -*- coding: utf-8 -*-
# This is "wormhole_" and not "wormhole" because "wormhole" will throw/raise
# import errors when using py2app-generated executables (presumably due to
# namespace-related conflicts with the "magic-wormhole" package/dependency)

import json
import logging

from PyQt5.QtCore import pyqtSignal, QObject
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from wormhole import wormhole
from wormhole.errors import WormholeError
from wormhole.tor_manager import get_tor

from gridsync import settings
from gridsync.errors import UpgradeRequiredError, TorError


APPID = settings['wormhole']['appid']
RELAY = settings['wormhole']['relay']


class Wormhole(QObject):

    got_welcome = pyqtSignal(dict)
    got_code = pyqtSignal(str)
    got_introduction = pyqtSignal()
    got_message = pyqtSignal(dict)
    closed = pyqtSignal()
    send_completed = pyqtSignal()

    def __init__(self, use_tor=False):
        super(Wormhole, self).__init__()
        self.use_tor = use_tor
        self._wormhole = wormhole.create(APPID, RELAY, reactor)

    @inlineCallbacks
    def connect(self):
        tor = None
        if self.use_tor:
            tor = yield get_tor(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")
            self._wormhole = wormhole.create(APPID, RELAY, reactor, tor=tor)
        logging.debug("Connecting to %s (tor=%s)...", RELAY, tor)
        welcome = yield self._wormhole.get_welcome()
        logging.debug("Connected to wormhole server; got welcome: %s", welcome)
        self.got_welcome.emit(welcome)

    @inlineCallbacks
    def close(self):
        logging.debug("Closing wormhole...")
        try:
            yield self._wormhole.close()
        except WormholeError:
            pass
        logging.debug("Wormhole closed.")
        self.closed.emit()

    @inlineCallbacks
    def receive(self, code):
        yield self.connect()
        self._wormhole.set_code(code)
        logging.debug("Using code: %s (APPID is '%s')", code, APPID)

        client_intro = {"abilities": {"client-v1": {}}}
        self._wormhole.send_message(json.dumps(client_intro).encode('utf-8'))

        data = yield self._wormhole.get_message()
        data = json.loads(data.decode('utf-8'))
        offer = data.get('offer', None)
        if offer:
            logging.warning(
                "The message-sender appears to be using the older, "
                "'xfer_util'-based version of the invite protocol.")
            msg = None
            if 'message' in offer:
                msg = json.loads(offer['message'])
                ack = {'answer': {'message_ack': 'ok'}}
                self._wormhole.send_message(json.dumps(ack).encode('utf-8'))
            else:
                raise Exception("Unknown offer type: {}".format(offer.keys()))
        else:
            logging.debug("Received server introduction: %s", data)
            if 'abilities' not in data:
                raise UpgradeRequiredError
            if 'server-v1' not in data['abilities']:
                raise UpgradeRequiredError
            self.got_introduction.emit()

            msg = yield self._wormhole.get_message()
            msg = json.loads(msg.decode("utf-8"))

        logging.debug("Received message: %s", msg)
        self.got_message.emit(msg)
        yield self.close()
        return msg

    @inlineCallbacks
    def send(self, msg, code=None):
        yield self.connect()
        if code is None:
            self._wormhole.allocate_code()
            logging.debug("Generating code...")
            code = yield self._wormhole.get_code()
            self.got_code.emit(code)
        else:
            self._wormhole.set_code(code)
        logging.debug("Using code: %s (APPID is '%s')", code, APPID)

        server_intro = {"abilities": {"server-v1": {}}}
        self._wormhole.send_message(json.dumps(server_intro).encode('utf-8'))

        data = yield self._wormhole.get_message()
        data = json.loads(data.decode('utf-8'))
        logging.debug("Received client introduction: %s", data)
        if 'abilities' not in data:
            raise UpgradeRequiredError
        if 'client-v1' not in data['abilities']:
            raise UpgradeRequiredError
        self.got_introduction.emit()

        logging.debug("Sending message: %s", msg)
        self._wormhole.send_message(json.dumps(msg).encode('utf-8'))
        yield self.close()
        self.send_completed.emit()


@inlineCallbacks
def wormhole_receive(code, use_tor=False):
    w = Wormhole(use_tor)
    msg = yield w.receive(code)
    return msg


@inlineCallbacks
def wormhole_send(msg, code=None, use_tor=False):
    w = Wormhole(use_tor)
    yield w.send(msg, code)
