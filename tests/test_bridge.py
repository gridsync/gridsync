import os

import pytest
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


@inlineCallbacks
def test_start_with_custom_port(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    port = get_free_port()
    address = yield bridge.start("http://example.org:11111", port)
    assert address.endswith(":" + str(port))


@inlineCallbacks
def test_start_with_tls(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=True)
    port = get_free_port()
    address = yield bridge.start("http://example.org:11111", port)
    assert address.startswith("https://")


@inlineCallbacks
def test_get_public_certificate(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=True)
    port = get_free_port()
    yield bridge.start("http://example.org:11111", port)
    public_bytes = bridge.get_public_certificate()
    assert public_bytes.decode().startswith("-----BEGIN CERTIFICATE-----")


@inlineCallbacks
def test_get_certificate_digest(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=True)
    port = get_free_port()
    yield bridge.start("http://example.org:11111", port)
    digest = bridge.get_certificate_digest()
    assert len(digest) == 32


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


@inlineCallbacks
def test_load_bridge_url_from_disk(tahoe):
    bridgeurl_file_contents = f"http://127.0.0.1:{get_free_port()}"
    with open(os.path.join(tahoe.nodedir, "private", "bridge.url"), "w") as f:
        f.write(bridgeurl_file_contents)
    bridge = Bridge(tahoe, reactor, use_tls=False)
    bridge_address = yield bridge.start(f"http://127.0.0.1:{get_free_port()}")
    assert bridge_address == bridgeurl_file_contents


@inlineCallbacks
def test_start_return_empty_address_on_cannot_listen_error(tahoe):
    bridgeurl_file_contents = f"http://invalid.example.org:{get_free_port()}"
    with open(os.path.join(tahoe.nodedir, "private", "bridge.url"), "w") as f:
        f.write(bridgeurl_file_contents)
    bridge = Bridge(tahoe, reactor, use_tls=False)
    bridge_address = yield bridge.start(f"http://127.0.0.1:{get_free_port()}")
    assert bridge_address == ""


@inlineCallbacks
def test_load_bridge_url_raise_value_error_for_missing_hostname(tahoe):
    bridgeurl_file_contents = "http://:12345"
    with open(os.path.join(tahoe.nodedir, "private", "bridge.url"), "w") as f:
        f.write(bridgeurl_file_contents)
    bridge = Bridge(tahoe, reactor, use_tls=False)
    with pytest.raises(ValueError):
        yield bridge.start(f"http://127.0.0.1:{get_free_port()}")


@inlineCallbacks
def test_load_bridge_url_raise_value_error_for_missing_port(tahoe):
    bridgeurl_file_contents = "http://127.0.0.1"
    with open(os.path.join(tahoe.nodedir, "private", "bridge.url"), "w") as f:
        f.write(bridgeurl_file_contents)
    bridge = Bridge(tahoe, reactor, use_tls=False)
    with pytest.raises(ValueError):
        yield bridge.start(f"http://127.0.0.1:{get_free_port()}")


@inlineCallbacks
def test_start_raise_value_error_for_missing_nodeurl_hostname(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    with pytest.raises(ValueError):
        yield bridge.start("http://:12345")


@inlineCallbacks
def test_start_raise_value_error_for_missing_nodeurl_port(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    with pytest.raises(ValueError):
        yield bridge.start("http://127.0.0.1")


@inlineCallbacks
def test_stop(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    yield bridge.start("http://example.org:11111")
    before = bridge.proxy.connected
    yield bridge.stop()
    after = bridge.proxy.connected
    assert (before, after) == (True, False)


@inlineCallbacks
def test_stop_is_idempotent(tahoe):
    bridge = Bridge(tahoe, reactor, use_tls=False)
    yield bridge.start("http://example.org:11111")
    before = bridge.proxy.connected
    yield bridge.stop()
    yield bridge.stop()
    after = bridge.proxy.connected
    assert (before, after) == (True, False)
