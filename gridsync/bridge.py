from __future__ import annotations

import datetime
import errno
import logging
import os
import socket
from random import randint
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from twisted.internet import ssl
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import SSL4ServerEndpoint, TCP4ServerEndpoint
from twisted.web.proxy import ReverseProxyResource
from twisted.web.server import Site

from gridsync.types import TwistedDeferred

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


def get_local_network_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(("10.255.255.255", 1))
    ip = s.getsockname()[0]
    s.close()
    return ip


def get_free_port(
    port: int = 0, range_min: int = 1024, range_max: int = 65535
) -> int:
    if not port:
        port = randint(range_min, range_max)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                logging.debug("Trying to bind to port: %i", port)
                s.bind(("127.0.0.1", port))
            except socket.error as err:
                logging.debug("Couldn't bind to port %i: %s", port, err)
                if err.errno == errno.EADDRINUSE:
                    port = randint(range_min, range_max)
                    continue
                raise
            logging.debug("Port %s is free", port)
            return port


class Bridge:
    def __init__(self, reactor) -> None:  # type: ignore
        self._reactor = reactor
        self.proxy = None
        self.address = ""

    @inlineCallbacks
    def start(self, nodeurl: str, port: int = 8089) -> TwistedDeferred[None]:
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return
        lan_ip = get_local_network_ip()
        logging.debug(
            "Starting bridge: http://%s:%s -> %s ...", lan_ip, port, nodeurl
        )
        endpoint = TCP4ServerEndpoint(self._reactor, port, interface=lan_ip)
        url = urlparse(nodeurl)
        self.proxy = yield endpoint.listen(
            Site(ReverseProxyResource(url.hostname, url.port, b""))
        )
        host = self.proxy.getHost()  # type: ignore
        self.address = f"http://{host.host}:{host.port}"
        logging.debug("Bridge started: %s", self.address)

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        if not self.proxy or not self.proxy.connected:
            logging.warning("Tried to stop a bridge that was not running")
            return
        host = self.proxy.getHost()
        logging.debug(
            "Stopping bridge: http://%s:%s ...", host.host, host.port
        )
        yield self.proxy.stopListening()
        logging.debug("Bridge stopped: http://%s:%s", host.host, host.port)
        self.proxy = None


class TLSBridge:
    def __init__(self, gateway: Tahoe, reactor) -> None:  # type: ignore
        self.gateway = gateway
        self._reactor = reactor
        self.pemfile = os.path.join(gateway.nodedir, "private", "bridge.pem")
        self.urlfile = os.path.join(gateway.nodedir, "private", "bridge.url")
        self.proxy = None
        self.address = ""
        self.__certificate_digest: bytes = b""

    def create_certificate(self, common_name: str) -> None:
        key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name(
            [x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, common_name)]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365 * 100)
            )
            .sign(key, hashes.SHA256())
        )

        with open(self.pemfile, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                + cert.public_bytes(serialization.Encoding.PEM)
            )
        self.__certificate_digest = cert.fingerprint(hashes.SHA256())

    def get_certificate_digest(self) -> bytes:
        if not self.__certificate_digest:
            with open(self.pemfile) as f:
                cert = x509.load_pem_x509_certificate(f.read().encode())
            self.__certificate_digest = cert.fingerprint(hashes.SHA256())
        return self.__certificate_digest

    @inlineCallbacks
    def start(self, nodeurl: str, port: int = 0) -> TwistedDeferred[None]:
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return
        lan_ip = get_local_network_ip()
        if os.path.exists(self.urlfile):
            with open(self.urlfile) as f:
                url = urlparse(f.read().strip())
            lan_ip, port = url.hostname, url.port
            # TODO: Check that hostname matches lan_ip
        else:
            if not port:
                port = get_free_port(range_min=49152, range_max=65535)
            with open(self.urlfile, "wb") as f:
                f.write(f"https://{lan_ip}:{port}".encode())
        logging.debug(
            "Starting bridge: https://%s:%s -> %s ...", lan_ip, port, nodeurl
        )
        if not os.path.exists(self.pemfile):
            self.create_certificate(lan_ip + ".invalid")  # XXX
        with open(self.pemfile) as f:
            certificate = ssl.PrivateCertificate.loadPEM(f.read()).options()
        endpoint = SSL4ServerEndpoint(
            self._reactor, port, certificate, interface=lan_ip
        )
        url = urlparse(nodeurl)
        self.proxy = yield endpoint.listen(
            Site(ReverseProxyResource(url.hostname, url.port, b""))
        )
        host = self.proxy.getHost()  # type: ignore
        self.address = f"https://{host.host}:{host.port}"
        d = iter(self.get_certificate_digest().hex().upper())
        fp = ":".join(a + b for a, b in zip(d, d))
        logging.debug(
            "Bridge started: %s (certificate digest: %s)", self.address, fp
        )

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        if not self.proxy or not self.proxy.connected:
            logging.warning("Tried to stop a bridge that was not running")
            return
        host = self.proxy.getHost()
        logging.debug(
            "Stopping bridge: https://%s:%s ...", host.host, host.port
        )
        yield self.proxy.stopListening()
        logging.debug("Bridge stopped: https://%s:%s", host.host, host.port)
        self.proxy = None
