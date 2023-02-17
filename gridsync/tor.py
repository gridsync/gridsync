# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from typing import Optional

import txtorcon
from qtpy.QtWidgets import QMessageBox, QWidget
from twisted.internet.defer import inlineCallbacks
from twisted.internet.interfaces import IReactorCore

from gridsync import features
from gridsync.types_ import TwistedDeferred

# From https://styleguide.torproject.org/visuals/
# "The main Tor Project color is Purple. Use Dark Purple as a secondary option"
TOR_PURPLE = "#7D4698"
TOR_DARK_PURPLE = "#59316B"
TOR_GREEN = "#68B030"
TOR_GREY = "#F8F9FA"
TOR_DARK_GREY = "#484848"
TOR_WHITE = "#FFFFFF"


def tor_required(furl: str) -> bool:
    try:
        hints = furl.split("/")[2].split(",")
    except (AttributeError, IndexError):
        return False
    num_matches = 0
    for hint in hints:
        if ".onion:" in hint:
            num_matches += 1
    return bool(num_matches and num_matches == len(hints))


@inlineCallbacks
def get_tor(reactor: IReactorCore) -> TwistedDeferred[txtorcon.Tor]:
    # TODO: Add launch option?
    tor = None
    if not features.tor:
        return tor
    logging.debug("Looking for a running Tor daemon...")
    try:
        tor = yield txtorcon.connect(reactor)
    except RuntimeError as exc:
        logging.debug(
            "Could not connect to a running Tor daemon: %s", str(exc)
        )
    if tor:
        logging.debug("Connected to Tor daemon (%s)", tor.version)
    return tor


@inlineCallbacks
def get_tor_with_prompt(
    reactor: IReactorCore, parent: Optional[QWidget] = None
) -> TwistedDeferred[txtorcon.Tor]:
    tor = yield get_tor(reactor)
    while not tor:
        msgbox = QMessageBox(parent)
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setWindowTitle("Tor Required")
        msgbox.setText(
            "This connection can only be made over the Tor network, however, "
            "no running Tor daemon was found or Tor has been disabled."
        )
        msgbox.setInformativeText(
            "Please ensure that Tor is running and try again.<p>For help "
            "installing Tor, visit "
            "<a href=https://torproject.org>https://torproject.org</a>"
        )
        msgbox.setStandardButtons(QMessageBox.Abort | QMessageBox.Retry)
        if msgbox.exec_() == QMessageBox.Retry:
            tor = yield get_tor(reactor)
        else:
            break
    return tor
