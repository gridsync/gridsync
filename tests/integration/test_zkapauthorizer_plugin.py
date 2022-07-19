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
    await client.create_client(settings)
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
