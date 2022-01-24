import os
import sys

import cerctifi
import treq
from pytest_twisted import inlineCallbacks


@inlineCallbacks
def test_tls(reactor):
    if sys.platform == "win32":
        os.environ["SSL_CERT_FILE"] = certifi.where()
    resp = yield treq.get("https://github.com")
    assert resp.code == 200
