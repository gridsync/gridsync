import os
import time

from pytest_twisted import async_yield_fixture, inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync.crypto import randstr
from gridsync.tahoe import Tahoe

os.environ["PATH"] = (
    os.path.join(os.getcwd(), "dist", "magic-folder")
    + os.pathsep
    + os.environ["PATH"]
)


@async_yield_fixture(scope="module")
async def magic_folder(tahoe_client):
    mf = tahoe_client.magic_folder
    await mf.start()
    yield mf
    mf.stop()


@async_yield_fixture(scope="module")
async def alice_magic_folder(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
    print("Alice's client nodedir:", client.nodedir)
    settings = {
        "nickname": "Test Grid",
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "1",
        "storage": {
            "test-grid-storage-server-1": {
                "nickname": "test-grid-storage-server-1",
                "anonymous-storage-FURL": tahoe_server.storage_furl,
            }
        },
    }
    await client.create_client(**settings)
    await client.start()
    yield client.magic_folder
    await client.stop()


@async_yield_fixture(scope="module")
async def bob_magic_folder(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
    print("Bob's client nodedir:", client.nodedir)
    settings = {
        "nickname": "Test Grid",
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "1",
        "storage": {
            "test-grid-storage-server-1": {
                "nickname": "test-grid-storage-server-1",
                "anonymous-storage-FURL": tahoe_server.storage_furl,
            }
        },
    }
    await client.create_client(**settings)
    await client.start()
    yield client.magic_folder
    await client.stop()


@inlineCallbacks
def until(predicate, timeout=10, period=0.2):
    limit = time.time() + timeout
    while time.time() < limit:
        result = predicate()
        if result:
            return result
        yield deferLater(reactor, period, lambda: None)
    raise TimeoutError(f"Timeout {timeout} seconds hit for {predicate}")


@inlineCallbacks
def test_version(magic_folder):
    output = yield magic_folder.version()
    assert output.startswith("Magic")


@inlineCallbacks
def test_restart(magic_folder):
    yield magic_folder.restart()


@inlineCallbacks
def test_get_folders(magic_folder):
    folders = yield magic_folder.get_folders()
    assert folders == {}


@inlineCallbacks
def test_add_folder(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    folders = yield magic_folder.get_folders()
    assert folder_name in folders


@inlineCallbacks
def test_leave_folder(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    folders = yield magic_folder.get_folders()
    folder_was_added = folder_name in folders

    yield magic_folder.leave_folder(folder_name)
    folders = yield magic_folder.get_folders()
    folder_was_removed = folder_name not in folders

    assert (folder_was_added, folder_was_removed) == (True, True)


@inlineCallbacks
def test_get_participants(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    participants = yield magic_folder.get_participants(folder_name)
    assert author in participants


@inlineCallbacks
def test_add_participant(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    author_name = randstr()
    dircap = yield magic_folder.gateway.mkdir()
    personal_dmd = yield magic_folder.gateway.diminish(dircap)
    yield magic_folder.add_participant(folder_name, author_name, personal_dmd)
    participants = yield magic_folder.get_participants(folder_name)
    assert author_name in participants


@inlineCallbacks
def test_get_snapshots(magic_folder):
    folders = yield magic_folder.get_folders()
    snapshots = yield magic_folder.get_snapshots()
    assert sorted(snapshots.keys()) == sorted(folders.keys())


@inlineCallbacks
def test_add_snapshot(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    filename = randstr()
    filepath = path / filename
    filepath.write_text(randstr() * 10)
    yield magic_folder.add_snapshot(folder_name, filename)
    snapshots = yield magic_folder.get_snapshots()
    assert filename in snapshots.get(folder_name)


@inlineCallbacks
def test_snapshot_uploads_to_personal_dmd(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    filename = randstr()
    filepath = path / filename
    filepath.write_text(randstr() * 10)
    yield magic_folder.add_snapshot(folder_name, filename)

    folders = yield magic_folder.get_folders()
    upload_dircap = folders[folder_name]["upload_dircap"]

    yield deferLater(reactor, 1.5, lambda: None)

    content = yield magic_folder.gateway.get_json(upload_dircap)
    assert filename in content[1]["children"]


@inlineCallbacks
def test_get_file_status(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    filename = randstr()
    filepath = path / filename
    filepath.write_text(randstr() * 10)
    yield magic_folder.add_snapshot(folder_name, filename)
    yield deferLater(reactor, 1.5, lambda: None)

    output = yield magic_folder.get_file_status(folder_name)
    keys = output[0].keys()
    assert ("mtime" in keys, "name" in keys, "size" in keys) == (
        True,
        True,
        True,
    )


@inlineCallbacks
def test_create_backup_cap(magic_folder):
    cap = yield magic_folder.create_backup_cap()
    assert cap.startswith("URI:DIR2")


@inlineCallbacks
def test_get_backup_cap(magic_folder):
    cap = yield magic_folder.get_backup_cap()
    assert cap.startswith("URI:DIR2")


@inlineCallbacks
def test_store_backup_cap_as_attribute(magic_folder):
    cap = yield magic_folder.get_backup_cap()
    assert magic_folder.backup_cap == cap


@inlineCallbacks
def test_backup_folder(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.backup_folder(folder_name)

    backup_cap = yield magic_folder.get_backup_cap()
    content = yield magic_folder.gateway.get_json(backup_cap)
    children = content[1]["children"]
    assert (
        f"{folder_name} (collective)" in children
        and f"{folder_name} (personal)" in children
    )


@inlineCallbacks
def test_get_remote_folders(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.backup_folder(folder_name)

    remote_folders = yield magic_folder.get_remote_folders()
    assert folder_name in remote_folders


@inlineCallbacks
def test_local_folders_have_backups(magic_folder):
    remote_folders = yield magic_folder.get_remote_folders()
    folders = yield magic_folder.get_folders()
    for folder in folders:
        assert folder in remote_folders


@inlineCallbacks
def test_restore_folder(magic_folder, tmp_path):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.backup_folder(folder_name)
    yield magic_folder.leave_folder(folder_name)
    yield magic_folder.restart()

    local_path = tmp_path / folder_name
    yield magic_folder.restore_folder(folder_name, local_path)
    folders = yield magic_folder.get_folders()
    assert folder_name in folders


@inlineCallbacks
def test_alice_add_folder(alice_magic_folder, tmp_path):
    folder_name = "ToBob"
    alice_path = tmp_path / folder_name
    yield alice_magic_folder.add_folder(alice_path, "Alice", poll_interval=1)

    filename = "SharedFile.txt"
    filepath = alice_path / filename
    filepath.write_text(randstr() * 10)
    yield alice_magic_folder.add_snapshot(folder_name, filename)

    snapshots = yield alice_magic_folder.get_snapshots()
    assert filename in snapshots.get(folder_name)


@inlineCallbacks
def test_bob_receive_folder(alice_magic_folder, bob_magic_folder, tmp_path):
    folder_name = "FromAlice"
    bob_path = tmp_path / folder_name
    yield bob_magic_folder.add_folder(bob_path, "Bob", poll_interval=1)

    alice_folders = yield alice_magic_folder.get_folders()
    alice_personal_dmd = yield alice_magic_folder.gateway.diminish(
        alice_folders["ToBob"]["upload_dircap"]
    )
    yield bob_magic_folder.add_participant(
        folder_name, "Alice", alice_personal_dmd
    )

    p = bob_path / "SharedFile.txt"
    succeeded = yield until(p.exists)
    assert succeeded is True


@inlineCallbacks
def test_folders_in_status_api_message(magic_folder, qtbot):
    with qtbot.wait_signal(
        magic_folder.monitor.status_message_received
    ) as blocker:
        yield magic_folder.restart()
        yield deferLater(reactor, 1, lambda: None)
    assert "folders" in blocker.args[0].get("state")


@inlineCallbacks
def test_monitor_emits_synchronizing_state_changed_signal(
    magic_folder, tmp_path, qtbot
):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    # FIXME: Using two "with" statements instead of qtbot.wait_signals
    # due to https://github.com/pytest-dev/pytest-qt/issues/316
    with qtbot.wait_signal(
        magic_folder.monitor.synchronizing_state_changed
    ), qtbot.wait_signal(magic_folder.monitor.synchronizing_state_changed):
        yield magic_folder.restart()
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.add_snapshot(folder_name, filename)
        yield deferLater(reactor, 1.5, lambda: None)


@inlineCallbacks
def test_monitor_emits_sync_started_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(magic_folder.monitor.sync_started) as blocker:
        yield magic_folder.restart()
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.add_snapshot(folder_name, filename)
        yield deferLater(reactor, 1.5, lambda: None)
    assert blocker.args == []


@inlineCallbacks
def test_monitor_emits_sync_stopped_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(magic_folder.monitor.sync_stopped) as blocker:
        yield magic_folder.restart()
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.add_snapshot(folder_name, filename)
        yield deferLater(reactor, 2, lambda: None)
    assert blocker.args == []


@inlineCallbacks
def test_monitor_emits_folder_added_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.monitor.do_check()
    with qtbot.wait_signal(magic_folder.monitor.folder_added) as blocker:
        yield magic_folder.add_folder(path, author)
        yield magic_folder.monitor.do_check()
    assert blocker.args == [folder_name]


@inlineCallbacks
def test_monitor_emits_folder_removed_signal(magic_folder, tmp_path, qtbot):
    # Removing existing folders first
    folders = yield magic_folder.get_folders()
    for folder in folders:
        yield magic_folder.leave_folder(folder)
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    yield magic_folder.monitor.do_check()
    with qtbot.wait_signal(magic_folder.monitor.folder_removed) as blocker:
        yield magic_folder.leave_folder(folder_name)
        yield magic_folder.monitor.do_check()
    assert blocker.args == [folder_name]


def test_eliot_logs_collected(magic_folder):
    assert len(magic_folder.get_logs()) > 0