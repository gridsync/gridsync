import os
import sys
from errno import EADDRINUSE
from json import dumps
from urllib.parse import urlsplit

import pytest
from autobahn.twisted.websocket import (
    WebSocketServerFactory,
    WebSocketServerProtocol,
)
from pytest_twisted import inlineCallbacks
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.error import CannotListenError
from twisted.internet.task import deferLater

from gridsync.network import get_free_port
from gridsync.websocket import WebSocketReaderService


def test_do_nothing_before_start(reactor):
    """
    ``WebSocketReaderService`` doesn't connect to anything before it
    is started.
    """
    assert reactor.connectTCP.call_count == 0


def test_connect_to_nodeurl(reactor):
    """
    When ``WebSocketReaderService`` starts, it tries to connect to the
    specified WebSocket endpoint.
    """
    wsurl = "ws://example.invalid:12345"
    wsreader = WebSocketReaderService(wsurl, {}, reactor=reactor)
    wsreader.start()

    host, port, factory = reactor.connectTCP.call_args[0]
    expected_url = urlsplit(wsurl)

    assert "{}:{}".format(host, port) == expected_url.netloc


def fake_log_server(protocol):
    from twisted.internet import reactor

    while True:
        port_number = get_free_port()
        # Why do you make me know the port number in advance, Autobahn?
        factory = WebSocketServerFactory(
            "ws://127.0.0.1:{}".format(port_number)
        )
        factory.protocol = protocol

        try:
            server_port = reactor.listenTCP(port_number, factory)
        except CannotListenError as e:
            if e.socketError.errno == EADDRINUSE:
                continue
            raise
        else:
            break

    return server_port


class FakeLogServerProtocol(WebSocketServerProtocol):
    FAKE_MESSAGE = dumps({"fake": "message"})

    def onOpen(self):
        self.sendMessage(self.FAKE_MESSAGE.encode("utf-8"), isBinary=False)


def twlog():
    from sys import stdout

    from twisted.logger import globalLogBeginner, textFileLogObserver

    globalLogBeginner.beginLoggingTo([textFileLogObserver(stdout)])


def connect_to_ws_endpoint(
    reactor, real_reactor, protocolClass, collector=None
):
    server_port = fake_log_server(protocolClass)
    server_addr = server_port.getHost()

    # Make sure the websocket client can compute the correct ws url.
    # If it doesn't match the server, the handshake fails.
    wsurl = f"ws://{server_addr.host}:{server_addr.port}/v1/test"
    wsreader = WebSocketReaderService(
        wsurl, {"test": 123}, reactor=reactor, collector=collector
    )
    wsreader.start()

    _, _, client_factory = reactor.connectTCP.call_args[0]

    endpoint = TCP4ClientEndpoint(
        real_reactor,
        # Windows doesn't like to connect to 0.0.0.0.
        "127.0.0.1" if server_addr.host == "0.0.0.0" else server_addr.host,
        server_addr.port,
    )
    return endpoint.connect(client_factory)


@inlineCallbacks
def test_collector(reactor):
    """
    The ``collector`` function saves messages from the WebSocket endpoint.
    """
    from twisted.internet import reactor as real_reactor

    messages = []

    yield connect_to_ws_endpoint(
        reactor,
        real_reactor,
        FakeLogServerProtocol,
        collector=lambda x: messages.append(x),
    )
    # Arbitrarily give it about a second to deliver the message.  All the I/O
    # is loopback and the data is small.  One second should be plenty of time.
    for i in range(20):
        if FakeLogServerProtocol.FAKE_MESSAGE in messages:
            break
        yield deferLater(real_reactor, 0.1, lambda: None)
    assert FakeLogServerProtocol.FAKE_MESSAGE in messages


@inlineCallbacks
def test_binary_messages_dropped(reactor):
    from twisted.internet import reactor as real_reactor

    class BinaryMessageServerProtocol(WebSocketServerProtocol):
        def onOpen(self):
            self.sendMessage(b"this is a binary message", isBinary=True)
            self.transport.loseConnection()

    messages = []

    client = yield connect_to_ws_endpoint(
        reactor,
        real_reactor,
        BinaryMessageServerProtocol,
        collector=lambda x: messages.append(x),
    )
    # client is a _WrappingProtocol because the implementation uses
    # TCP4ClientEndpoint which puts a _WrappingFactory into the reactor.  Then
    # connect_to_ws_endpoint takes the _WrappingFactory out of the _mock_
    # reactor it supplied and puts it into a new TCP4ClientEndpoint and uses
    # that against a real reactor.  The connection gets set up and the
    # _WrappingFactory creates a _WrappingProtocol which the new
    # TCP4ClientEndpoint happily hands back to us.
    #
    # Sadly, this hack makes us dependent on the implementation of endpoints,
    # the use of endpoints in streamedlogs.py, and the use of endpoints in
    # connect_to_ws_endpoint.
    #
    # Maybe it would be good to try to use twisted.test.iosim instead?  Or
    # build something like RequestTraversalAgent but for Autobahn/WebSocket.
    yield client._wrappedProtocol.is_closed
    assert messages == []


def advance_mock_clock(reactor):
    for call in reactor.callLater.call_args_list:
        args, kwargs = call
        delay, func = args[:2]
        posargs = args[2:]
        func(*posargs, **kwargs)


@pytest.mark.skipif(
    "CI" in os.environ and sys.platform == "win32",
    reason="Fails intermittently on GitHub Actions' Windows runners",
)
@inlineCallbacks
def test_reconnect_to_websocket(reactor):
    """
    If the connection to the WebSocket endpoint is lost, an attempt
    is made to re-establish.
    """
    # This test might be simpler and more robust if it used
    # twisted.internet.task.Clock and twisted.test.proto_helpers.MemoryReactor
    # instead of a Mock reactor.
    from twisted.internet import reactor as real_reactor

    client_protocol = yield connect_to_ws_endpoint(
        reactor, real_reactor, FakeLogServerProtocol
    )
    original_host, original_port = client_protocol.transport.addr
    client_protocol.transport.abortConnection()

    # Let the reactor process the disconnect.
    yield deferLater(real_reactor, 0.0, lambda: None)

    advance_mock_clock(reactor)
    assert reactor.connectTCP.call_count == 2
    reconnect_host, reconnect_port, _ = reactor.connectTCP.call_args[0]

    assert (original_host, original_port) == (reconnect_host, reconnect_port)


@inlineCallbacks
def test_stop_prevents_reconnecting(reactor):
    """
    ``WebSocketReaderService`` stops trying to reconnect when its
    ``stop`` method is called.
    """
    from twisted.internet import reactor as real_reactor

    server_port = fake_log_server(FakeLogServerProtocol)
    server_addr = server_port.getHost()

    wsurl = f"ws://{server_addr.host}:{server_addr.port}/v1/test"
    wsreader = WebSocketReaderService(wsurl, {"test": 123}, reactor=reactor)
    wsreader.start()

    _, _, client_factory = reactor.connectTCP.call_args[0]

    endpoint = TCP4ClientEndpoint(
        real_reactor,
        # Windows doesn't like to connect to 0.0.0.0.
        "127.0.0.1" if server_addr.host == "0.0.0.0" else server_addr.host,
        server_addr.port,
    )
    client_protocol = yield endpoint.connect(client_factory)

    wsreader.stop()
    client_protocol.transport.abortConnection()

    # Let the reactor process the disconnect.
    yield deferLater(real_reactor, 0.0, lambda: None)

    advance_mock_clock(reactor)

    assert reactor.connectTCP.call_count == 1


@inlineCallbacks
def test_path(reactor):
    """
    The request is made to the correct path on the server to reach the
    WebSocket endpoint.
    """
    from twisted.internet import reactor as real_reactor

    path = Deferred()

    class PathCheckingProtocol(WebSocketServerProtocol):
        def onConnect(self, request):
            path.callback(request.path)

    yield connect_to_ws_endpoint(reactor, real_reactor, PathCheckingProtocol)
    p = yield path
    assert p == "/v1/test"


@inlineCallbacks
def test_headers(reactor):
    """
    The request to the WebSocket endpoint includes pecified headers
    """
    from twisted.internet import reactor as real_reactor

    headers = Deferred()

    class AuthorizationCheckingProtocol(WebSocketServerProtocol):
        def onConnect(self, request):
            headers.callback(request.headers)

    yield connect_to_ws_endpoint(
        reactor, real_reactor, AuthorizationCheckingProtocol
    )
    h = yield headers
    assert h.get("test") == "123"
