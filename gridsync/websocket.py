import logging
from typing import Callable, Optional
from urllib.parse import urlparse

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
)
from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint


class WebSocketReaderProtocol(
    WebSocketClientProtocol
):  # pylint: disable=too-many-ancestors
    def onOpen(self) -> None:
        logging.debug("WebSocket connection opened.")

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if isBinary:
            logging.warning(
                "Received a binary-mode WebSocket message; dropping."
            )
            return
        message = payload.decode("utf-8")
        self.factory.collector(message)  # XXX

    def onClose(self, wasClean: bool, code: int, reason: str) -> None:
        logging.debug(
            "WebSocket connection closed: %s (code %s)", reason, code
        )


class WebSocketReaderService(MultiService):
    def __init__(
        self,
        url: str,
        headers: Optional[dict],
        collector: Optional[Callable] = logging.debug,
    ) -> None:
        super().__init__()
        self.url = url
        self.headers = headers
        self.collector = collector

        self._client_service: Optional[ClientService] = None

    def _create_client_service(self) -> ClientService:
        parsed = urlparse(self.url)
        endpoint = TCP4ClientEndpoint(reactor, parsed.hostname, parsed.port)
        factory = WebSocketClientFactory(self.url, headers=self.headers)
        factory.protocol = WebSocketReaderProtocol
        factory.collector = self.collector
        client_service = ClientService(endpoint, factory, clock=reactor)
        return client_service

    def stop(self) -> None:
        if self.running and self._client_service:
            self._client_service.disownServiceParent()
            self._client_service = None
            return super().stopService()
        return None

    def start(self) -> None:
        if not self.running:
            self._client_service = self._create_client_service()
            self._client_service.setServiceParent(self)
            return super().startService()
        return None
