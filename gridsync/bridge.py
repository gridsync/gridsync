from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Dict, Union
from urllib.parse import urlparse

from twisted.internet import ssl
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import SSL4ServerEndpoint, TCP4ServerEndpoint
from twisted.web.proxy import ReverseProxyResource
from twisted.web.resource import Resource
from twisted.web.server import Site

from gridsync.crypto import (
    create_certificate,
    get_certificate_digest,
    get_certificate_public_bytes,
    randstr,
)
from gridsync.network import get_free_port, get_local_network_ip
from gridsync.types import TwistedDeferred

# pylint: disable=ungrouped-imports
if TYPE_CHECKING:
    from twisted.internet.interfaces import IReactorCore
    from twisted.web.server import Request

    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class SingleServeResource(Resource):
    def __init__(self, content: bytes):
        super().__init__()
        self.content = content

    def render_GET(self, _: Request) -> bytes:
        return self.content


class BridgeReverseProxyResource(ReverseProxyResource):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        bridge: Bridge,
        host: str,
        port: int,
        path: bytes,
        reactor: IReactorCore,
    ) -> None:
        super().__init__(host, port, path, reactor)
        self.bridge = bridge

    def getChild(
        self, path: bytes, request: Request
    ) -> Union[ReverseProxyResource, SingleServeResource]:
        self.bridge.resource_requested(request)
        content = self.bridge.single_serve_content.pop(path, b"")
        if content:
            self.bridge.on_token_redeemed(path)
            return SingleServeResource(content)
        return super().getChild(path, request)


class Bridge:
    def __init__(
        self, gateway: Tahoe, reactor: IReactorCore, use_tls: bool = True
    ) -> None:
        self.gateway = gateway
        self._reactor = reactor
        self.use_tls = use_tls
        if use_tls:
            self.scheme = "https"
        else:
            self.scheme = "http"
        self.pemfile = os.path.join(gateway.nodedir, "private", "bridge.pem")
        self.urlfile = os.path.join(gateway.nodedir, "private", "bridge.url")
        self.proxy = None
        self.address = ""
        self.__certificate_digest: bytes = b""
        self.__certificate_public_bytes: bytes = b""
        self.single_serve_content: Dict[bytes, bytes] = {}
        self.pending_links: Dict[str, str] = {}

    def get_public_certificate(self) -> bytes:
        if not self.__certificate_public_bytes:
            self.__certificate_public_bytes = get_certificate_public_bytes(
                self.pemfile
            )
        return self.__certificate_public_bytes

    def get_certificate_digest(self) -> bytes:
        if not self.__certificate_digest:
            self.__certificate_digest = get_certificate_digest(self.pemfile)
        return self.__certificate_digest

    def _create_endpoint(
        self, ip: str, port: int
    ) -> Union[SSL4ServerEndpoint, TCP4ServerEndpoint]:
        if self.use_tls:
            if not os.path.exists(self.pemfile):
                self.__certificate_digest = create_certificate(
                    self.pemfile, ip + ".invalid", ip
                )
            with open(self.pemfile) as f:
                cert = ssl.PrivateCertificate.loadPEM(f.read()).options()
            return SSL4ServerEndpoint(self._reactor, port, cert, interface=ip)
        return TCP4ServerEndpoint(self._reactor, port, interface=ip)

    @inlineCallbacks
    def start(self, nodeurl: str, port: int = 0) -> TwistedDeferred[None]:
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return

        if os.path.exists(self.urlfile):
            with open(self.urlfile) as f:
                url = urlparse(f.read().strip())
            bridge_host, bridge_port = url.hostname, url.port
            if not bridge_host:
                raise ValueError(
                    f"Bridge hostname not found in {self.urlfile}"
                )
            if not bridge_port:
                raise ValueError(f"Bridge port not found in {self.urlfile}")
            # TODO: Check that hostname matches lan_ip
            # TODO: Check/verify scheme
        else:
            bridge_host = get_local_network_ip()
            if port:
                bridge_port = port
            else:
                bridge_port = get_free_port()
            with open(self.urlfile, "w") as f:
                f.write(f"{self.scheme}://{bridge_host}:{bridge_port}")

        logging.debug(
            "Starting bridge: %s://%s:%s -> %s ...",
            self.scheme,
            bridge_host,
            bridge_port,
            nodeurl,
        )

        url = urlparse(nodeurl)
        node_host, node_port = url.hostname, url.port
        if not node_host:
            raise ValueError("Node hostname not found")
        if not node_port:
            raise ValueError("Node port not found")

        endpoint = self._create_endpoint(bridge_host, bridge_port)
        self.proxy = yield endpoint.listen(
            Site(
                BridgeReverseProxyResource(
                    self, node_host, node_port, b"", self._reactor
                )
            )
        )
        host = self.proxy.getHost()  # type: ignore
        self.address = f"{self.scheme}://{host.host}:{host.port}"
        if self.use_tls:
            d = iter(self.get_certificate_digest().hex().upper())
            fp = ":".join(a + b for a, b in zip(d, d))
            logging.debug(
                "Bridge started: %s (certificate digest: %s)", self.address, fp
            )
        else:
            logging.debug("Bridge started: %s", self.address)

    @staticmethod
    def resource_requested(request: Request) -> None:
        logging.debug(
            "%s %s %s", request.getClientIP(), request.method, request.uri
        )

    def add_pending_link(self, device_name: str, device_cap: str) -> str:
        token = randstr(32)
        self.single_serve_content[token.encode()] = device_cap.encode()
        self.pending_links[token] = device_name
        return token

    def on_token_redeemed(self, token: bytes) -> None:
        device_name = self.pending_links.pop(token.decode(), "")
        self.gateway.devices_manager.device_linked.emit(device_name)  # XXX
        logging.debug("Device linked: %s", device_name)

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        if not self.proxy or not self.proxy.connected:
            logging.warning("Tried to stop a bridge that was not running")
            return
        host = self.proxy.getHost()
        logging.debug(
            "Stopping bridge: %s://%s:%s ...",
            self.scheme,
            host.host,
            host.port,
        )
        yield self.proxy.stopListening()
        logging.debug(
            "Bridge stopped: %s://%s:%s", self.scheme, host.host, host.port
        )
        self.proxy = None
