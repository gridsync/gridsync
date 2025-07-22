import pytest
from pytest_twisted import inlineCallbacks

from gridsync import features

# "pytestmark" is a special global variable that can be used to apply marks at
# the module level. See https://docs.pytest.org/en/stable/example/markers.html
pytestmark = pytest.mark.skipif(
    not features.zkapauthorizer,
    reason="zkapauthorizer plugin not enabled",
)


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
