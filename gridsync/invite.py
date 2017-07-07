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
from gridsync.errors import UpgradeRequiredError


APPID = settings['wormhole']['appid']
RELAY = settings['wormhole']['relay']


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
    logging.debug("Using code: %s (APPID is '%s')", code, APPID)

    client_intro = {"abilities": {"client-v1": {}}}
    wh.send_message(json.dumps(client_intro).encode('utf-8'))

    data = yield wh.get_message()
    data = json.loads(data.decode('utf-8'))
    offer = data.get('offer', None)
    if offer:
        logging.warning("The message-sender appears to be using the older, "
                        "'xfer_util'-based version of the invite protocol.")
        msg = None
        if 'message' in offer:
            msg = offer['message']
            ack = {'answer': {'message_ack': 'ok'}}
            wh.send_message(json.dumps(ack).encode('utf-8'))
        else:
            raise Exception("Unknown offer type: {}".format(offer.keys()))
    else:
        logging.debug("Received server introduction: %s", data)
        if 'abilities' not in data:
            raise UpgradeRequiredError
        if 'server-v1' not in data['abilities']:
            raise UpgradeRequiredError

        msg = yield wh.get_message()
        msg = json.loads(msg.decode("utf-8"))

    logging.debug("Received message: %s", msg)
    yield wh.close()
    returnValue(msg)
