import pytest
from pytest_twisted import inlineCallbacks
from twisted.internet.defer import Deferred, DeferredList


@pytest.fixture()
def rootcap_manager(tahoe_client):
    return tahoe_client.rootcap_manager


@inlineCallbacks
def test_create_rootcap_doesnt_override_existing_rootcap(rootcap_manager):
    created_caps = set()
    results_1 = yield DeferredList(
        [
            Deferred.fromCoroutine(rootcap_manager.create_rootcap())
            for _ in range(5)
        ]
    )
    results_2 = yield DeferredList(
        [
            Deferred.fromCoroutine(rootcap_manager.create_rootcap())
            for _ in range(5)
        ]
    )
    for result in results_1 + results_2:
        _, output = result
        created_caps.add(output)
    assert len(created_caps) == 1  # Only one cap was created


@inlineCallbacks
def test_add_backup(tahoe_client, rootcap_manager):
    1 / 0
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield Deferred.fromCoroutine(
        rootcap_manager.add_backup("TestBackups-1", "backup-1", dircap)
    )
    backups = yield Deferred.fromCoroutine(
        rootcap_manager.get_backups("TestBackups-1")
    )
    assert "backup-1" in backups


@inlineCallbacks
def test_remove_backup(tahoe_client, rootcap_manager):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield Deferred.fromCoroutine(
        rootcap_manager.add_backup("TestBackups-2", "backup-2", dircap)
    )
    yield Deferred.fromCoroutine(
        rootcap_manager.remove_backup("TestBackups-2", "backup-2")
    )
    backups = yield Deferred.fromCoroutine(
        rootcap_manager.get_backups("TestBackups-2")
    )
    assert "backup-2" not in backups


@inlineCallbacks
def test_remove_backup_is_idempotent(tahoe_client, rootcap_manager):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield Deferred.fromCoroutine(
        rootcap_manager.add_backup("TestBackups-3", "backup-3", dircap)
    )
    yield Deferred.fromCoroutine(
        rootcap_manager.remove_backup("TestBackups-3", "backup-3")
    )
    exception_raised = None
    try:
        yield Deferred.fromCoroutine(
            rootcap_manager.remove_backup("TestBackups-3", "backup-3")
        )
    except Exception as exc:
        exception_raised = exc
    assert not exception_raised
