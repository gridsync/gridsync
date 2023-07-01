# -*- coding: utf-8 -*-
# This is "wormhole_" and not "wormhole" because "wormhole" will throw/raise
# import errors when using py2app-generated executables (presumably due to
# namespace-related conflicts with the "magic-wormhole" package/dependency)
from __future__ import annotations

import json
import logging
from typing import Optional

from qtpy.QtCore import QObject, Signal
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from wormhole import wormhole
from wormhole.errors import WormholeError
from wormhole.tor_manager import get_tor

from gridsync import settings
from gridsync.errors import TorError, UpgradeRequiredError
from gridsync.types_ import TwistedDeferred

APPID = settings["wormhole"]["appid"]
RELAY = settings["wormhole"]["relay"]


class Wormhole(QObject):
    got_welcome = Signal(dict)
    got_code = Signal(str)
    got_introduction = Signal()
    got_message = Signal(dict)
    closed = Signal()
    send_completed = Signal()

    def __init__(self, use_tor: bool = False) -> None:
        super().__init__()
        self.use_tor = use_tor
        self._wormhole: Optional[wormhole] = None

    @inlineCallbacks
    def connect(self) -> TwistedDeferred[None]:
        tor = None
        if self.use_tor:
            tor = yield get_tor(reactor)
            if not tor:
                raise TorError("Could not connect to a running Tor daemon")
            self._wormhole = wormhole.create(APPID, RELAY, reactor, tor=tor)
        else:
            self._wormhole = wormhole.create(APPID, RELAY, reactor)
        logging.debug("Connecting to %s (tor=%s)...", RELAY, tor)
        welcome = yield self._wormhole.get_welcome()
        logging.debug("Connected to wormhole server; got welcome: %s", welcome)
        self.got_welcome.emit(welcome)

    @inlineCallbacks
    def close(self) -> TwistedDeferred[None]:
        logging.debug("Closing wormhole...")
        if not self._wormhole:
            logging.warning("No wormhole was created; returning")
            return
        try:
            yield self._wormhole.close()
        except WormholeError:
            pass
        logging.debug("Wormhole closed.")
        self.closed.emit()

    @inlineCallbacks
    def receive(self, code: str) -> TwistedDeferred[str]:
        yield self.connect()
        self._wormhole.set_code(code)  # type: ignore
        logging.debug("Using code: %s (APPID is '%s')", code, APPID)

        client_intro: dict = {"abilities": {"client-v1": {}}}
        self._wormhole.send_message(json.dumps(client_intro).encode("utf-8"))  # type: ignore

        data = yield self._wormhole.get_message()  # type: ignore
        data = json.loads(data.decode("utf-8"))
        offer = data.get("offer", None)
        if offer:
            logging.warning(
                "The message-sender appears to be using the older, "
                "'xfer_util'-based version of the invite protocol."
            )
            msg = None
            if "message" in offer:
                msg = json.loads(offer["message"])
                ack = {"answer": {"message_ack": "ok"}}
                self._wormhole.send_message(json.dumps(ack).encode("utf-8"))  # type: ignore
            else:
                raise Exception(  # pylint: disable=broad-exception-raised
                    "Unknown offer type: {}".format(offer.keys())
                )
        else:
            logging.debug("Received server introduction: %s", data)
            if "abilities" not in data:
                raise UpgradeRequiredError
            if "server-v1" not in data["abilities"]:
                raise UpgradeRequiredError
            self.got_introduction.emit()

            msg = yield self._wormhole.get_message()  # type: ignore
            msg = json.loads(msg.decode("utf-8"))

        logging.debug("Received wormhole message.")
        self.got_message.emit(msg)
        yield self.close()
        return msg

    @inlineCallbacks
    def send(
        self, msg: str, code: Optional[str] = None
    ) -> TwistedDeferred[None]:
        yield self.connect()
        if code is None:
            self._wormhole.allocate_code()  # type: ignore
            logging.debug("Generating code...")
            code = yield self._wormhole.get_code()  # type: ignore
            self.got_code.emit(code)
        else:
            self._wormhole.set_code(code)  # type: ignore
        logging.debug("Using code: %s (APPID is '%s')", code, APPID)

        server_intro: dict = {"abilities": {"server-v1": {}}}
        self._wormhole.send_message(json.dumps(server_intro).encode("utf-8"))  # type: ignore

        data = yield self._wormhole.get_message()  # type: ignore
        data = json.loads(data.decode("utf-8"))
        logging.debug("Received client introduction: %s", data)
        if "abilities" not in data:
            raise UpgradeRequiredError
        if "client-v1" not in data["abilities"]:
            raise UpgradeRequiredError
        self.got_introduction.emit()

        logging.debug("Sending wormhole message...")
        self._wormhole.send_message(json.dumps(msg).encode("utf-8"))  # type: ignore
        yield self.close()
        self.send_completed.emit()


@inlineCallbacks
def wormhole_receive(code: str, use_tor: bool = False) -> TwistedDeferred[str]:
    w = Wormhole(use_tor)
    msg = yield w.receive(code)
    return msg


@inlineCallbacks
def wormhole_send(
    msg: str, code: Optional[str] = None, use_tor: bool = False
) -> TwistedDeferred[None]:
    w = Wormhole(use_tor)
    yield w.send(msg, code)
