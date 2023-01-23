from pytest_twisted import ensureDeferred, inlineCallbacks

from gridsync.tahoe import TahoeWebError


@inlineCallbacks
def test_zkapauthorizer_version(zkapauthorizer):
    version = yield zkapauthorizer.get_version()
    assert version != ""


@inlineCallbacks
def test_zkapauthorizer_add_and_get_voucher():
    voucher = yield zkapauthorizer.add_voucher()
    output = yield zkapauthorizer.get_voucher(voucher)
    assert output["number"] == voucher


@inlineCallbacks
def test_zkapauthorizer_calculate_price(zkapauthorizer):
    output = yield zkapauthorizer.calculate_price([1024, 2048, 3072, 4096])
    assert output["price"] == 4


@ensureDeferred
async def test_no_html_in_server_error(zkapauthorizer):
    try:
        await zkapauthorizer.gateway.mkdir()
    except TahoeWebError as e:
        assert "<!DOCTYPE html>" not in str(e)
