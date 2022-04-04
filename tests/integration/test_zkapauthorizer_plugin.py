from pytest_twisted import async_yield_fixture, inlineCallbacks

from gridsync.tahoe import Tahoe
from gridsync.zkapauthorizer import PLUGIN_NAME


@async_yield_fixture(scope="module")
async def zkapauthorizer(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
    settings = {
        "nickname": "ZKAPAuthorizer-enabled Test Grid",
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "1",
        "storage": {
            "test-grid-storage-server-1": {
                "anonymous-storage-FURL": "pb://@tcp:/",
                "nickname": "test-grid-storage-server-1",
                "storage-options": [
                    {
                        "name": PLUGIN_NAME,
                        "ristretto-issuer-root-url": "https://example.org/",
                        "storage-server-FURL": tahoe_server.storage_furl,
                        "allowed-public-keys": "AAAAAAAAAAAAAAAA",
                    }
                ],
            }
        },
    }
    await client.create_client(**settings)
    client.save_settings(settings)
    await client.start()
    yield client.zkapauthorizer
    await client.stop()


@inlineCallbacks
def test_zkapauthorizer_version(zkapauthorizer):
    version = yield zkapauthorizer.get_version()
    assert version != ""


@inlineCallbacks
def test_zkapauthorizer_add_and_get_voucher(zkapauthorizer):
    voucher = yield zkapauthorizer.add_voucher()
    output = yield zkapauthorizer.get_voucher(voucher)
    assert output["number"] == voucher


@inlineCallbacks
def test_zkapauthorizer_calculate_price(zkapauthorizer):
    output = yield zkapauthorizer.calculate_price([1024, 2048, 3072, 4096])
    assert output["price"] == 4


@inlineCallbacks
def test_replicate_creates_cap(zkapauthorizer):
    cap = yield zkapauthorizer.replicate()
    assert cap.startswith("URI:")


@inlineCallbacks
def test_replicate_is_idempotent(zkapauthorizer):
    cap_1 = yield zkapauthorizer.replicate()
    cap_2 = yield zkapauthorizer.replicate()
    assert cap_1 == cap_2


@inlineCallbacks
def test_get_recovery_status(zkapauthorizer):
    status = yield zkapauthorizer.get_recovery_status()
    assert status is not None  # XXX
