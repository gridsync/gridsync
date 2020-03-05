import os
import webbrowser

import treq
from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks

from gridsync import config_dir
from gridsync.tahoe import Tahoe


@react
@inlineCallbacks
def main(reactor):
    t = Tahoe(os.path.join(config_dir, "PrivateStorage Staging"))
    yield t.start()
    yield t.await_ready()
    new = yield t.add_voucher(None)
    voucher = yield t.get_voucher(new)
    print(voucher)
    payment_url = t.zkap_payment_url(new)
    print(payment_url)
    webbrowser.open(payment_url)
    zkaps = yield t.get_zkaps(1)
    print(zkaps)
    yield t.stop()
