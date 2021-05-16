import treq
from pytest_twisted import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.web.resource import Resource
from twisted.web.server import Site

from gridsync.bridge import Bridge
from gridsync.crypto import randstr
from gridsync.network import get_free_port


@inlineCallbacks
def test_start_creates_address(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    address = yield bridge.start("http://example.org:11111")
    assert address != ""


@inlineCallbacks
def test_start_is_idempotent(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    address_1 = yield bridge.start("http://example.org:11111")
    address_2 = yield bridge.start("http://example.org:11111")
    assert address_1 == address_2


class FakeResource(Resource):
    isLeaf = True

    def __init__(self, content):
        self.content = content

    def render_GET(self, request):
        return self.content


@inlineCallbacks
def test_reverse_proxy_passthrough(tahoe):
    expected = b"TestContent" + randstr().encode()
    endpoint = TCP4ServerEndpoint(
        reactor, get_free_port(), interface="127.0.0.1"
    )
    port = yield endpoint.listen(Site(FakeResource(expected)))
    fake_nodeurl = f"http://127.0.0.1:{port.port}"

    bridge = Bridge(tahoe, reactor, use_tls=False)
    bridge_address = yield bridge.start(fake_nodeurl)

    resp = yield treq.get(bridge_address)
    content = yield treq.content(resp)
    assert content == expected


@inlineCallbacks
def test_single_serve_resource(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    yield bridge.start("http://example.org:11111")
    cap = "URI:DIR2:test:test"
    token = bridge.add_pending_link("TestDevice", cap)
    resp = yield treq.get(bridge.address + "/" + token)
    content = yield treq.content(resp)
    assert content == cap.encode()
