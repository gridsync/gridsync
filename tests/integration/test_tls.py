import treq
from pytest_twisted import inlineCallbacks


@inlineCallbacks
def test_tls(reactor):
    resp = yield treq.get("https://github.com")
    assert resp.code == 200
