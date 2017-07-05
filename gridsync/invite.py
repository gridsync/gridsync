# -*- coding: utf-8 -*-

import json
import logging

from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from wormhole import wormhole
try:
    from wormhole.wordlist import raw_words
except ImportError:  # TODO: Switch to new magic-wormhole completion API
    from wormhole._wordlist import raw_words

from gridsync import settings

APPID = settings['wormhole']['appid']
RELAY = settings['wormhole']['relay']
#APPID = "tahoe-lafs.org/lafs"  # XXX
# https://github.com/tahoe-lafs/tahoe-lafs/pull/418#pullrequestreview-47916533

wordlist = []
for word in raw_words.items():
    wordlist.extend(word[1])
wordlist = sorted([word.lower() for word in wordlist])


def is_valid(code):
    words = code.split('-')
    if len(words) != 3:
        return False
    elif not words[0].isdigit():
        return False
    elif not words[1] in wordlist:
        return False
    elif not words[2] in wordlist:
        return False
    return True


@inlineCallbacks
def wormhole_receive(code):
    logging.debug("Connecting to %s...", RELAY)
    wh = wormhole.create(APPID, RELAY, reactor)
    welcome = yield wh.get_welcome()
    logging.debug("Connected to wormhole server; got welcome: %s", welcome)
    wh.set_code(code)
    logging.debug("Using code: %s", code)

    client_intro = {"abilities": {"client-v1": {}}}
    wh.send_message(json.dumps(client_intro).encode("utf-8"))

    server_intro = yield wh.get_message()
    server_intro = json.loads(server_intro.decode("utf-8"))
    logging.debug("Received server introduction: %s", server_intro)

    # XXX: raise UpgradeRequiredError? Handle "old" xfer_util-based protocol?
    if 'abilities' not in server_intro:
        raise Exception("No 'abilities' in server introduction")
    if 'server-v1' not in server_intro['abilities']:
        raise Exception("No 'server-v1' in server abilities")

    msg = yield wh.get_message()
    msg = json.loads(msg.decode("utf-8"))
    logging.debug("Received message: %s", msg)

    yield wh.close()
    returnValue(msg)
