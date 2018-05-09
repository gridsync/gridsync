# -*- coding: utf-8 -*-

import logging

from twisted.internet.defer import inlineCallbacks
import txtorcon


# From https://styleguide.torproject.org/visuals/
# "The main Tor Project color is Purple. Use Dark Purple as a secondary option"
TOR_PURPLE = '#7D4698'
TOR_DARK_PURPLE = '#59316B'
TOR_GREEN = '#68B030'
TOR_GREY = '#F8F9FA'
TOR_DARK_GREY = '#484848'
TOR_WHITE = '#FFFFFF'


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
