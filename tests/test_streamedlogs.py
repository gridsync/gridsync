from errno import EADDRINUSE
from json import dumps
from random import randrange
from urllib.parse import urlsplit

from autobahn.twisted.websocket import (
    WebSocketServerFactory,
    WebSocketServerProtocol,
)
from pytest_twisted import inlineCallbacks
from twisted.internet.defer import Deferred
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.error import CannotListenError
from twisted.internet.task import deferLater

from gridsync.streamedlogs import StreamedLogs


def test_do_nothing_before_start(reactor, tahoe):
    """
    ``StreamedLogs`` doesn't connect to anything before it is started.
    """
    assert reactor.connectTCP.call_count == 0


def test_connect_to_nodeurl(reactor, tahoe):
    """
    When ``StreamedLogs`` starts it tries to connect to the streaming log
    WebSocket endpoint run by the Tahoe-LAFS node.
    """
    nodeurl = "http://example.invalid:12345"
    tahoe.streamedlogs.start(nodeurl, "api-token")

    host, port, factory = reactor.connectTCP.call_args[0]
    expected_url = urlsplit(nodeurl)

    assert "{}:{}".format(host, port) == expected_url.netloc


def fake_log_server(protocol):
    from twisted.internet import reactor

    while True:
        port_number = randrange(10000, 60000)
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


def connect_to_log_endpoint(reactor, tahoe, real_reactor, protocolClass):
    server_port = fake_log_server(protocolClass)
    server_addr = server_port.getHost()

    # Make sure the streamed logs websocket client can compute the correct ws
    # url.  If it doesn't match the server, the handshake fails.
    tahoe.nodeurl = "http://{}:{}".format(server_addr.host, server_addr.port)
    tahoe.streamedlogs.start(tahoe.nodeurl, tahoe.api_token)
    _, _, client_factory = reactor.connectTCP.call_args[0]

    endpoint = TCP4ClientEndpoint(
        real_reactor,
        # Windows doesn't like to connect to 0.0.0.0.
        "127.0.0.1" if server_addr.host == "0.0.0.0" else server_addr.host,
        server_addr.port,
    )
    return endpoint.connect(client_factory)


@inlineCallbacks
def test_collect_eliot_logs(reactor, tahoe):
    """
    ``StreamedLogs`` saves the JSON log messages so that they can be retrieved
    using ``Tahoe.get_streamed_log_messages``.
    """
    from twisted.internet import reactor as real_reactor

    yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, FakeLogServerProtocol
    )

    # Arbitrarily give it about a second to deliver the message.  All the I/O
    # is loopback and the data is small.  One second should be plenty of time.
    for i in range(20):
        messages = tahoe.get_streamed_log_messages()
        if FakeLogServerProtocol.FAKE_MESSAGE in messages:
            break
        yield deferLater(real_reactor, 0.1, lambda: None)

    messages = tahoe.get_streamed_log_messages()
    assert FakeLogServerProtocol.FAKE_MESSAGE in messages


def test_bounded_streamed_log_buffer(reactor, tahoe):
    """
    Only a limited number of the most recent messages remain in the streamed
    log message buffer.
    """
    maxlen = 3
    streamedlogs = StreamedLogs(reactor, maxlen=maxlen)
    for i in range(maxlen + 1):
        streamedlogs.add_message("{}".format(i).encode("ascii"))

    actual = streamedlogs.get_streamed_log_messages()
    expected = list("{}".format(i) for i in range(1, maxlen + 1))
    assert actual == expected


class BinaryMessageServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        self.sendMessage(b"this is a binary message", isBinary=True)
        self.transport.loseConnection()


@inlineCallbacks
def test_binary_messages_dropped(reactor, tahoe):
    from twisted.internet import reactor as real_reactor

    server = BinaryMessageServerProtocol()

    client = yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, lambda: server
    )
    # client is a _WrappingProtocol because the implementation uses
    # TCP4ClientEndpoint which puts a _WrappingFactory into the reactor.  Then
    # connect_to_log_endpoint takes the _WrappingFactory out of the _mock_
    # reactor it supplied and puts it into a new TCP4ClientEndpoint and uses
    # that against a real reactor.  The connection gets set up and the
    # _WrappingFactory creates a _WrappingProtocol which the new
    # TCP4ClientEndpoint happily hands back to us.
    #
    # Sadly, this hack makes us dependent on the implementation of endpoints,
    # the use of endpoints in streamedlogs.py, and the use of endpoints in
    # connect_to_log_endpoint.
    #
    # Maybe it would be good to try to use twisted.test.iosim instead?  Or
    # build something like RequestTraversalAgent but for Autobahn/WebSocket.
    yield client._wrappedProtocol.is_closed

    assert tahoe.streamedlogs.get_streamed_log_messages() == []


def advance_mock_clock(reactor):
    for call in reactor.callLater.call_args_list:
        args, kwargs = call
        delay, func = args[:2]
        posargs = args[2:]
        func(*posargs, **kwargs)


@inlineCallbacks
def test_reconnect_to_websocket(reactor, tahoe):
    """
    If the connection to the WebSocket endpoint is lost, an attempt is made to
    re-establish.
    """
    # This test might be simpler and more robust if it used
    # twisted.internet.task.Clock and twisted.test.proto_helpers.MemoryReactor
    # instead of a Mock reactor.
    from twisted.internet import reactor as real_reactor

    client_protocol = yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, FakeLogServerProtocol
    )
    client_protocol.transport.abortConnection()

    # Let the reactor process the disconnect.
    yield deferLater(real_reactor, 0.0, lambda: None)

    advance_mock_clock(reactor)
    assert reactor.connectTCP.call_count == 2
    host, port, _ = reactor.connectTCP.call_args[0]

    expected_url = urlsplit(tahoe.nodeurl)
    assert "{}:{}".format(host, port) == expected_url.netloc


@inlineCallbacks
def test_stop(reactor, tahoe):
    """
    ``StreamedLogs`` stops trying to reconnect when its ``stop`` method is
    called.
    """
    from twisted.internet import reactor as real_reactor

    client_protocol = yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, FakeLogServerProtocol
    )
    tahoe.streamedlogs.stop()
    client_protocol.transport.abortConnection()

    # Let the reactor process the disconnect.
    yield deferLater(real_reactor, 0.0, lambda: None)

    advance_mock_clock(reactor)

    assert reactor.connectTCP.call_count == 1


@inlineCallbacks
def test_path(reactor, tahoe):
    """
    The request is made to the correct path on the server to reach the
    WebSocket endpoint.
    """
    from twisted.internet import reactor as real_reactor

    path = Deferred()

    class PathCheckingProtocol(WebSocketServerProtocol):
        def onConnect(self, request):
            path.callback(request.path)

    yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, PathCheckingProtocol
    )
    p = yield path
    assert p == "/private/logs/v1"


@inlineCallbacks
def test_authentication(reactor, tahoe):
    """
    The request to the WebSocket endpoint includes the necessary
    *Authorization* header including the Tahoe-LAFS API token.
    """
    from twisted.internet import reactor as real_reactor

    api_token = "12345abcdef"
    tahoe.api_token = api_token

    headers = Deferred()

    class AuthorizationCheckingProtocol(WebSocketServerProtocol):
        def onConnect(self, request):
            headers.callback(request.headers)

    yield connect_to_log_endpoint(
        reactor, tahoe, real_reactor, AuthorizationCheckingProtocol
    )
    h = yield headers
    assert h.get("authorization", None) == "tahoe-lafs {}".format(api_token), h
