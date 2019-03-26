# -*- coding: utf-8 -*-

"""
Support for reading the streaming Eliot logs available from a Tahoe-LAFS
node.
"""

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
    _started = False

    def __init__(self, gateway):
        self._gateway = gateway

    def start(self):
        if not self._started:
            self._started = True
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
