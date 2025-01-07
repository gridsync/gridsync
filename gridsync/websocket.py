import logging
from typing import Callable, Optional, cast
from urllib.parse import urlparse

from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
)
from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet.endpoints import (
    IStreamClientEndpoint,
    TCP4ClientEndpoint,
)
from twisted.internet.interfaces import IReactorTime


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
        reactor: Optional[IReactorTime] = None,
    ) -> None:
        super().__init__()
        if reactor is None:
            from twisted.internet import reactor as imported_reactor

            # To avoid mypy "assignment" error ("expression has type Module")
            self._reactor = cast(IReactorTime, imported_reactor)
        else:
            self._reactor = reactor
        self.url = url
        self.headers = headers
        self.collector = collector

        self._client_service: Optional[ClientService] = None

    def _create_client_service(self) -> ClientService:
        parsed = urlparse(self.url)
        # Windows doesn't like to connect to 0.0.0.0.
        host = "127.0.0.1" if parsed.hostname == "0.0.0.0" else parsed.hostname
        if not isinstance(host, str) or not isinstance(parsed.port, int):
            raise ValueError(f"Invalid WebSocket URL: {self.url}")
        endpoint = TCP4ClientEndpoint(self._reactor, host, parsed.port)
        endpoint = cast(IStreamClientEndpoint, endpoint)
        factory = WebSocketClientFactory(self.url, headers=self.headers)
        factory.protocol = WebSocketReaderProtocol
        factory.collector = self.collector
        client_service = ClientService(endpoint, factory, clock=self._reactor)
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
