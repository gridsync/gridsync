import treq
from pytest_twisted import inlineCallbacks
from twisted.internet import reactor

from gridsync.bridge import Bridge


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


@inlineCallbacks
def test_single_serve_resource(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    yield bridge.start("http://example.org:11111")
    cap = "URI:DIR2:test:test"
    token = bridge.add_pending_link("TestDevice", cap)
    resp = yield treq.get(bridge.address + "/" + token)
    content = yield treq.content(resp)
    assert content == cap.encode()
