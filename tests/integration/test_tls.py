import os
import sys

import certifi
import treq
from pytest_twisted import inlineCallbacks


@inlineCallbacks
def test_tls(reactor):
    if sys.platform in ("win32", "darwin"):
        os.environ["SSL_CERT_FILE"] = certifi.where()
    resp = yield treq.get("https://github.com")
    assert resp.code == 200
