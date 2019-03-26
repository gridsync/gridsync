# -*- coding: utf-8 -*-

"""
Support for reading the streaming Eliot logs available from a Tahoe-LAFS
node.
"""

import logging
from collections import deque
from urllib.parse import urlsplit

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
)


class TahoeLogReader(WebSocketClientProtocol):
    def onMessage(self, payload, isBinary):
        if isBinary:
            logging.warning(
                "Received a binary-mode WebSocket message from Tahoe-LAFS "
                "streaming log; dropping.",
            )
        self.factory.streamedlogs._buffer.append(payload)


class StreamedLogs():
    """
    :ivar _reactor: A reactor that can connect using whatever transport the
        Tahoe-LAFS node requires (TCP, etc).

    :ivar Tahoe _gateway: The object representing the Tahoe-LAFS node from
        which this object will receive streamed logs.

    :ivar deque _buffer: Bounded storage for the streamed messages.
    """
    _started = False

    def __init__(self, reactor, gateway, maxlen=10000):
        self._reactor = reactor
        self._gateway = gateway
        self._buffer = deque(maxlen=maxlen)

    def start(self):
        if not self._started:
            self._started = True
            self._connect_log_reader()

    def get_streamed_log_messages(self):
        """
        :return list[str]: The messages currently in the message buffer.
        """
        return list(msg.decode("utf-8") for msg in self._buffer)

    def _connect_log_reader(self):
        nodeurl = self._gateway.nodeurl

        from hyperlink import parse
        url = parse(nodeurl)
        wsurl = url.replace(scheme="ws").child("private", "logs", "v1")

        factory = WebSocketClientFactory(
            url=wsurl.to_uri().to_text(),
            headers={
                "Authorization": "{} {}".format('tahoe-lafs', "abcd"),
            }
        )
        factory.protocol = TahoeLogReader
        factory.streamedlogs = self
        host, port = urlsplit(nodeurl).netloc.split(':')

        # endpoint = HostnameEndpoint(self._reactor, host, int(port))
        # ClientService(endpoint, factory).startService()

        self._reactor.connectTCP(host, int(port), factory)
