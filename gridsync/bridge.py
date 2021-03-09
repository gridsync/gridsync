import logging
import os
import secrets
import socket
from urllib.parse import urlparse

from OpenSSL import crypto
from twisted.internet import ssl
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import TCP4ServerEndpoint, SSL4ServerEndpoint
from twisted.web.proxy import ReverseProxyResource
from twisted.web.server import Site


def get_local_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(("10.255.255.255", 1))
    ip = s.getsockname()[0]
    s.close()
    return ip


class Bridge:
    def __init__(self, reactor):
        self._reactor = reactor
        self.proxy = None
        self.address = ""

    @inlineCallbacks
    def start(self, nodeurl, port=8089):
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
        host = self.proxy.getHost()
        self.address = f"http://{host.host}:{host.port}"
        logging.debug("Bridge started: %s", self.address)

    @inlineCallbacks
    def stop(self):
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
    def __init__(self, gateway, reactor):
        self.gateway = gateway
        self._reactor = reactor
        self.keyfile = os.path.join(gateway.nodedir, "private", "bridge.key")
        self.certfile = os.path.join(gateway.nodedir, "private", "bridge.crt")
        self.proxy = None
        self.address = ""
        self.certificate_digest: str = ""

    def create_certificate(self):  # XXX
        pkey = crypto.PKey()
        pkey.generate_key(crypto.TYPE_RSA, 2048)
        cert = crypto.X509()
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(100 * 365 * 24 * 60 * 60)
        cert.set_serial_number(secrets.randbits(128))
        cert.set_pubkey(pkey)
        cert.sign(pkey, "sha256")
        with open(self.keyfile, "wb") as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey))
        with open(self.certfile, "wb") as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    def get_certificate_digest(self) -> str:
        with open(self.certfile) as f:
            return (
                crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
                .digest("sha256")
                .decode("utf-8")
            )

    @inlineCallbacks
    def start(self, nodeurl, port=8090):
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return
        lan_ip = get_local_network_ip()
        logging.debug(
            "Starting bridge: https://%s:%s -> %s ...", lan_ip, port, nodeurl
        )
        if not os.path.exists(self.certfile):
            self.create_certificate()
        self.certificate_digest = self.get_certificate_digest()
        certificate = ssl.DefaultOpenSSLContextFactory(
            self.keyfile, self.certfile
        )
        endpoint = SSL4ServerEndpoint(
            self._reactor, port, certificate, interface=lan_ip
        )
        url = urlparse(nodeurl)
        self.proxy = yield endpoint.listen(
            Site(ReverseProxyResource(url.hostname, url.port, b""))
        )
        host = self.proxy.getHost()
        self.address = f"https://{host.host}:{host.port}"
        logging.debug(
            "Bridge started: %s (certificate digest: %s)",
            self.address,
            self.certificate_digest,
        )

    @inlineCallbacks
    def stop(self):
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
