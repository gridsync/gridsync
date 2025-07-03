import pytest
from pytest_twisted import inlineCallbacks

from gridsync.tahoe import ZKAPAUTHORIZER_AVAILABLE


@pytest.mark.skipif(
    not ZKAPAUTHORIZER_AVAILABLE,
    reason="zkapauthorizer plugin not available",
)
@inlineCallbacks
def test_zkapauthorizer_version(zkapauthorizer):
    version = yield zkapauthorizer.get_version()
    assert version != ""


@pytest.mark.skipif(
    not ZKAPAUTHORIZER_AVAILABLE,
    reason="zkapauthorizer plugin not available",
)
@inlineCallbacks
def test_zkapauthorizer_add_and_get_voucher(zkapauthorizer):
    voucher = yield zkapauthorizer.add_voucher()
    output = yield zkapauthorizer.get_voucher(voucher)
    assert output["number"] == voucher


@pytest.mark.skipif(
    not ZKAPAUTHORIZER_AVAILABLE,
    reason="zkapauthorizer plugin not available",
)
@inlineCallbacks
def test_zkapauthorizer_calculate_price(zkapauthorizer):
    output = yield zkapauthorizer.calculate_price([1024, 2048, 3072, 4096])
    assert output["price"] == 4
