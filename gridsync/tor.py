# -*- coding: utf-8 -*-

import logging

from twisted.internet.defer import inlineCallbacks
import txtorcon


class TorError(Exception):
    pass


@inlineCallbacks
def get_tor(reactor):  # TODO: Add launch option?
    tor = None
    logging.debug("Looking for a running Tor daemon...") 
    try:
        tor = yield txtorcon.connect(reactor)
    except RuntimeError:
        logging.debug("Could not connect to a running Tor daemon.")
    if tor:
        logging.debug("Connected to Tor daemon (%s)", tor.version)
    return tor
