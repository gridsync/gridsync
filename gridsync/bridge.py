import datetime
import logging
import os
import socket
from urllib.parse import urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from twisted.internet import ssl
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import SSL4ServerEndpoint, TCP4ServerEndpoint
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
        self.pemfile = os.path.join(gateway.nodedir, "private", "bridge.pem")
        self.proxy = None
        self.address = ""
        self.certificate_digest: bytes = b""

    def create_certificate(self):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = issuer = x509.Name([])
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
        self.certificate_digest = cert.fingerprint(hashes.SHA256())

    def get_certificate_digest(self) -> bytes:
        if not self.certificate_digest:
            with open(self.pemfile) as f:
                cert = x509.load_pem_x509_certificate(f.read().encode())
            self.certificate_digest = cert.fingerprint(hashes.SHA256())
        return self.certificate_digest

    @inlineCallbacks
    def start(self, nodeurl, port=8090):
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return
        lan_ip = get_local_network_ip()
        logging.debug(
            "Starting bridge: https://%s:%s -> %s ...", lan_ip, port, nodeurl
        )
        if not os.path.exists(self.pemfile):
            self.create_certificate()
        with open(self.pemfile) as f:
            certificate = ssl.PrivateCertificate.loadPEM(f.read()).options()
        endpoint = SSL4ServerEndpoint(
            self._reactor, port, certificate, interface=lan_ip
        )
        url = urlparse(nodeurl)
        self.proxy = yield endpoint.listen(
            Site(ReverseProxyResource(url.hostname, url.port, b""))
        )
        host = self.proxy.getHost()
        self.address = f"https://{host.host}:{host.port}"
        d = iter(self.get_certificate_digest().hex().upper())
        fp = ":".join(a + b for a, b in zip(d, d))
        logging.debug(
            "Bridge started: %s (certificate digest: %s)", self.address, fp
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
