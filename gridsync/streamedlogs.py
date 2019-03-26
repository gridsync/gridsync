# -*- coding: utf-8 -*-

"""
Support for reading the streaming Eliot logs available from a Tahoe-LAFS
node.
"""

import logging
from collections import deque
from urllib.parse import urlsplit

from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.application.internet import ClientService
from twisted.application.service import MultiService

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


class StreamedLogs(MultiService):
    """
    :ivar _reactor: A reactor that can connect using whatever transport the
        Tahoe-LAFS node requires (TCP, etc).

    :ivar Tahoe _gateway: The object representing the Tahoe-LAFS node from
        which this object will receive streamed logs.

    :ivar deque _buffer: Bounded storage for the streamed messages.
    """
    _started = False

    def __init__(self, reactor, gateway, maxlen=10000):
        super().__init__()
        self._reactor = reactor
        self._gateway = gateway
        self._buffer = deque(maxlen=maxlen)

    def start(self):
        if not self.running:
            self._client_service = self._create_client_service()
            self._client_service.setServiceParent(self)
            return super().startService()

    def stop(self):
        if self.running:
            self._client_service.disownServiceParent()
            self._client_service = None
            return super().stopService()

    def get_streamed_log_messages(self):
        """
        :return list[str]: The messages currently in the message buffer.
        """
        return list(msg.decode("utf-8") for msg in self._buffer)

    def _create_client_service(self):
        nodeurl = self._gateway.nodeurl

        from hyperlink import parse
        url = parse(nodeurl)
        wsurl = url.replace(scheme="ws").child("private", "logs", "v1")

        api_token = self._gateway.api_token
        factory = WebSocketClientFactory(
            url=wsurl.to_uri().to_text(),
            headers={
                "Authorization": "{} {}".format('tahoe-lafs', api_token),
            }
        )
        factory.protocol = TahoeLogReader
        factory.streamedlogs = self
        host, port = urlsplit(nodeurl).netloc.split(':')

        endpoint = TCP4ClientEndpoint(self._reactor, host, int(port))
        client_service = ClientService(endpoint, factory, clock=self._reactor)
        return client_service
