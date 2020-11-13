import logging
import socket
from urllib.parse import urlparse

from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.internet.defer import inlineCallbacks
from twisted.web.proxy import ReverseProxyResource
from twisted.web.server import Site


def get_local_network_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.connect(("<broadcast>", 0))
    ip = s.getsockname()[0]
    s.close()
    return ip


class Bridge:
    def __init__(self, reactor):
        self._reactor = reactor
        self.proxy = None

    @inlineCallbacks
    def start(self, nodeurl, port=8089):
        if self.proxy and self.proxy.connected:
            logging.warning("Tried to start a bridge that was already running")
            return None
        lan_ip = get_local_network_ip()
        logging.debug(
            f"Starting bridge: http://{lan_ip}:{port} -> {nodeurl} ..."
        )
        endpoint = TCP4ServerEndpoint(self._reactor, port, interface=lan_ip)
        url = urlparse(nodeurl)
        self.proxy = yield endpoint.listen(
            Site(ReverseProxyResource(url.hostname, url.port, b""))
        )
        host = self.proxy.getHost()
        logging.debug(f"Bridge started: http://{host.host}:{host.port}")

    @inlineCallbacks
    def stop(self):
        if not self.proxy or not self.proxy.connected:
            logging.warning("Tried to stop a bridge that was not running")
            return None
        host = self.proxy.getHost()
        logging.debug(f"Stopping bridge: http://{host.host}:{host.port} ...")
        yield self.proxy.stopListening()
        logging.debug(f"Bridge stopped: http://{host.host}:{host.port}")
        self.proxy = None
