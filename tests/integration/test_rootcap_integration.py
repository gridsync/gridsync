import pytest
from pytest_twisted import inlineCallbacks
from twisted.internet.defer import DeferredList


@pytest.fixture()
def rootcap_manager(tahoe_client):
    return tahoe_client.rootcap_manager


@inlineCallbacks
def test_create_rootcap_doesnt_override_existing_rootcap(rootcap_manager):
    created_caps = set()
    results_1 = yield DeferredList(
        [rootcap_manager.create_rootcap() for _ in range(5)]
    )
    results_2 = yield DeferredList(
        [rootcap_manager.create_rootcap() for _ in range(5)]
    )
    for result in results_1 + results_2:
        _, output = result
        created_caps.add(output)
    assert len(created_caps) == 1  # Only one cap was created
