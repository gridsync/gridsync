import os
import sys
import time
from pathlib import Path

import pytest
from pytest_twisted import async_yield_fixture, inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync import APP_NAME
from gridsync.crypto import randstr
from gridsync.magic_folder import MagicFolderStatus, MagicFolderWebError
from gridsync.tahoe import Tahoe

if sys.platform == "darwin":
    application_bundle_path = str(
        Path(
            os.getcwd(),
            "dist",
            APP_NAME + ".app",
            "Contents",
            "MacOS",
            "magic-folder",
        ).resolve()
    )
else:
    application_bundle_path = str(
        Path(os.getcwd(), "dist", APP_NAME, "magic-folder").resolve()
    )

os.environ["PATH"] = application_bundle_path + os.pathsep + os.environ["PATH"]


@async_yield_fixture(scope="module")
async def magic_folder(tahoe_client):
    mf = tahoe_client.magic_folder
    await mf.await_running()
    yield mf


@async_yield_fixture(scope="module")
async def alice_magic_folder(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
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
def leave_all_folders(magic_folder):
    folders = yield magic_folder.get_folders()
    for folder in list(folders):
        # https://github.com/LeastAuthority/magic-folder/issues/587
        yield deferLater(reactor, 0.1, lambda: None)
        yield magic_folder.leave_folder(folder)


@inlineCallbacks
def test_version(magic_folder):
    output = yield magic_folder.version()
    assert output.startswith("Magic")


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
def test_leave_folder_with_missing_ok_true(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    folders = yield magic_folder.get_folders()
    folder_was_added = folder_name in folders

    yield magic_folder.leave_folder(folder_name)
    yield magic_folder.leave_folder(folder_name, missing_ok=True)
    folders = yield magic_folder.get_folders()
    folder_was_removed = folder_name not in folders

    assert (folder_was_added, folder_was_removed) == (True, True)


@inlineCallbacks
def test_leave_folder_with_missing_ok_false(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    yield magic_folder.leave_folder(folder_name)
    with pytest.raises(MagicFolderWebError):
        yield magic_folder.leave_folder(folder_name, missing_ok=False)


@inlineCallbacks
def test_leave_folder_removes_from_magic_folders_dict(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    folders = yield magic_folder.get_folders()
    folder_was_added = folder_name in folders

    yield magic_folder.leave_folder(folder_name)
    folder_was_removed = folder_name not in magic_folder.magic_folders

    assert (folder_was_added, folder_was_removed) == (True, True)


@inlineCallbacks
def test_folder_is_local_true(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    assert magic_folder.folder_is_local(folder_name) is True


def test_folder_is_local_false(magic_folder, tmp_path):
    folder_name = randstr() + "_1"
    assert magic_folder.folder_is_local(folder_name) is False


@inlineCallbacks
def test_folder_is_remote_true(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    yield magic_folder.monitor.do_check()  # XXX
    assert magic_folder.folder_is_remote(folder_name) is True


def test_folder_is_remote_false(magic_folder, tmp_path):
    folder_name = randstr() + "_2"
    assert magic_folder.folder_is_remote(folder_name) is False


@inlineCallbacks
def test_folder_exists_true(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    assert magic_folder.folder_exists(folder_name) is True


def test_folder_exists_false(magic_folder, tmp_path):
    folder_name = randstr() + "_3"
    assert magic_folder.folder_is_local(folder_name) is False


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
def test_scanner_uploads_to_personal_dmd(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    filename = randstr()
    filepath = path / filename
    filepath.write_text(randstr() * 10)
    yield magic_folder.scan(folder_name)

    folders = yield magic_folder.get_folders()
    upload_dircap = folders[folder_name]["upload_dircap"]

    yield deferLater(reactor, 2.5, lambda: None)

    content = yield magic_folder.gateway.get_json(upload_dircap)
    assert filename in content[1]["children"]


@inlineCallbacks
def test_get_file_status(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    filename = randstr()
    filepath = path / filename
    filepath.write_text(randstr() * 10)
    yield magic_folder.scan(folder_name)

    output = yield magic_folder.get_file_status(folder_name)
    keys = output[0].keys()
    assert (
        "mtime" in keys,
        "relpath" in keys,
        "size" in keys,
        "last-updated" in keys,
    ) == (
        True,
        True,
        True,
        True,
    )


@inlineCallbacks
def test_get_object_sizes(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    filepath_1 = path / "TestFile1.txt"
    filepath_1.write_text(randstr(32) * 10)
    filepath_2 = path / "TestFile2.txt"
    filepath_2.write_text(randstr(32) * 10)
    yield magic_folder.scan(folder_name)
    yield deferLater(reactor, 1.5, lambda: None)
    # From https://github.com/LeastAuthority/magic-folder/blob/
    # 10421379e2e7154708ab9c7380b3da527c284027/docs/interface.rst#
    # get-v1magic-folderfolder-nametahoe-objects:
    # "The list is flat; if there are 2 Snapshots on the grid this will
    # return 6 integers."
    output = yield magic_folder.get_object_sizes(folder_name)
    assert output == [416, 320, 217, 416, 320, 217]


@inlineCallbacks
def test_get_all_object_sizes(magic_folder, tmp_path):
    yield leave_all_folders(magic_folder)

    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    filepath_1 = path / "TestFile1.txt"
    filepath_1.write_text(randstr(32) * 10)
    filepath_2 = path / "TestFile2.txt"
    filepath_2.write_text(randstr(32) * 10)
    yield magic_folder.scan(folder_name)

    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    filepath_3 = path / "TestFile3.txt"
    filepath_3.write_text(randstr(32) * 10)
    yield magic_folder.scan(folder_name)

    yield deferLater(reactor, 1.5, lambda: None)
    output = yield magic_folder.get_all_object_sizes()
    assert output == [416, 320, 217, 416, 320, 217, 416, 320, 217]


@inlineCallbacks
def test_scan(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    output = yield magic_folder.scan(folder_name)
    assert output == {}


@inlineCallbacks
def test_poll(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)

    output = yield magic_folder.poll(folder_name)
    assert output == {}


@inlineCallbacks
def test_create_folder_backup(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)

    backup_cap = yield magic_folder.rootcap_manager.get_backup_cap(
        ".magic-folders"
    )
    content = yield magic_folder.gateway.get_json(backup_cap)
    children = content[1]["children"]
    assert (
        f"{folder_name} (collective)" in children
        and f"{folder_name} (personal)" in children
    )


@inlineCallbacks
def test_get_folder_backups(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)

    remote_folders = yield magic_folder.get_folder_backups()
    assert folder_name in remote_folders


@inlineCallbacks
def test_remove_folder_backup(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)

    yield magic_folder.remove_folder_backup(folder_name)
    backup_cap = yield magic_folder.rootcap_manager.get_backup_cap(
        ".magic-folders"
    )
    content = yield magic_folder.gateway.get_json(backup_cap)
    children = content[1]["children"]
    assert (
        f"{folder_name} (collective)" not in children
        and f"{folder_name} (personal)" not in children
    )


@inlineCallbacks
def test_remote_magic_folders_dict_is_updated_by_folder_backups(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)
    backups = yield magic_folder.get_folder_backups()
    folder_backed_up = folder_name in backups
    folder_added = folder_name in magic_folder.remote_magic_folders
    yield magic_folder.remove_folder_backup(folder_name)
    folder_removed = folder_name not in magic_folder.remote_magic_folders
    assert folder_backed_up and folder_added and folder_removed


@inlineCallbacks
def test_create_folder_backup_preserves_collective_writecap(magic_folder):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)

    remote_folders = yield magic_folder.get_folder_backups()
    remote_cap = remote_folders[folder_name]["collective_dircap"]
    assert remote_cap.startswith("URI:DIR2:")


@inlineCallbacks
def test_local_folders_have_backups(magic_folder):
    remote_folders = yield magic_folder.get_folder_backups()
    folders = yield magic_folder.get_folders()
    for folder in folders:
        assert folder in remote_folders


@inlineCallbacks
def test_restore_folder_backup(magic_folder, tmp_path):
    folders = yield magic_folder.get_folders()
    folder_name = next(iter(folders))
    yield magic_folder.create_folder_backup(folder_name)
    yield magic_folder.leave_folder(folder_name)

    local_path = tmp_path / folder_name
    yield magic_folder.restore_folder_backup(folder_name, local_path)
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
    yield alice_magic_folder.scan(folder_name)

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
def test_monitor_emits_sync_progress_updated_signal(
    magic_folder, tmp_path, qtbot
):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(
        magic_folder.monitor.sync_progress_updated
    ) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield deferLater(reactor, 1, lambda: None)
    assert blocker.args == [folder_name, 0, 1]


@inlineCallbacks
def test_monitor_emits_upload_started_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(magic_folder.monitor.upload_started) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield deferLater(reactor, 1, lambda: None)
    assert (blocker.args[0], blocker.args[1]) == (folder_name, filename)


@inlineCallbacks
def test_monitor_emits_upload_finished_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(magic_folder.monitor.upload_finished) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield deferLater(reactor, 1, lambda: None)
    assert (blocker.args[0], blocker.args[1]) == (folder_name, filename)


@inlineCallbacks
def test_monitor_emits_files_updated_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)

    with qtbot.wait_signal(magic_folder.monitor.files_updated) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield deferLater(reactor, 1, lambda: None)
    assert blocker.args == [folder_name, [filename]]


def test_monitor_emits_error_occured_signal(magic_folder, tmp_path, qtbot):
    with qtbot.wait_signal(magic_folder.monitor.error_occurred) as blocker:
        magic_folder.monitor._check_errors(
            {
                "folders": {
                    "TestFolder": {
                        "downloads": [],
                        "errors": [{"timestamp": 1234567890, "summary": ":("}],
                        "uploads": [],
                        "recent": [],
                    }
                }
            },
            {},
        )
    assert blocker.args == ["TestFolder", ":(", 1234567890]


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
def test_monitor_emits_folder_added_signal_via_status_message(
    magic_folder, tmp_path, qtbot
):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(magic_folder.monitor.folder_added) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield deferLater(reactor, 2, lambda: None)
    assert blocker.args == [folder_name]


@inlineCallbacks
def test_monitor_emits_folder_mtime_updated_signal(
    magic_folder, tmp_path, qtbot
):
    yield leave_all_folders(magic_folder)
    yield magic_folder.monitor.do_check()
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(
        magic_folder.monitor.folder_mtime_updated
    ) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
        yield deferLater(reactor, 1, lambda: None)  # to increment mtime
        filepath.write_text(randstr() * 16)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert blocker.args[0] == folder_name


@pytest.mark.skipif(
    "CI" in os.environ,
    reason="Fails intermittently on GitHub Actions' Windows runners",
)
@inlineCallbacks
def test_monitor_emits_folder_size_updated_signal(
    magic_folder, tmp_path, qtbot
):
    yield leave_all_folders(magic_folder)
    yield magic_folder.monitor.do_check()
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(
        magic_folder.monitor.folder_size_updated
    ) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr(64))
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert (blocker.args[0], blocker.args[1]) == (folder_name, 64)


@inlineCallbacks
def test_monitor_emits_folder_removed_signal(magic_folder, tmp_path, qtbot):
    # Removing existing folders first
    yield leave_all_folders(magic_folder)

    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    yield magic_folder.monitor.do_check()
    with qtbot.wait_signal(magic_folder.monitor.folder_removed) as blocker:
        yield magic_folder.leave_folder(folder_name)
        yield magic_folder.monitor.do_check()
    assert blocker.args == [folder_name]


@inlineCallbacks
def test_monitor_emits_file_added_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(magic_folder.monitor.file_added) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert (blocker.args[0], blocker.args[1].get("relpath")) == (
        folder_name,
        filename,
    )


@pytest.mark.skipif(
    "CI" in os.environ,
    reason="Fails intermittently on GitHub Actions' Windows runners",
)
@inlineCallbacks
def test_monitor_emits_file_size_updated_signal(magic_folder, tmp_path, qtbot):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(magic_folder.monitor.file_size_updated) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
        filepath.write_text(randstr() * 16)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert (blocker.args[0], blocker.args[1].get("relpath")) == (
        folder_name,
        filename,
    )


@inlineCallbacks
def test_monitor_emits_file_mtime_updated_signal(
    magic_folder, tmp_path, qtbot
):
    yield leave_all_folders(magic_folder)
    yield magic_folder.monitor.do_check()
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(magic_folder.monitor.file_mtime_updated) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
        yield deferLater(reactor, 1, lambda: None)  # to increment mtime
        filepath.write_text(randstr() * 16)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
        yield deferLater(reactor, 1, lambda: None)  # to increment mtime
        filepath.write_text(randstr() * 16)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert (blocker.args[0], blocker.args[1].get("relpath")) == (
        folder_name,
        filename,
    )


@pytest.mark.skipif(
    "CI" in os.environ,
    reason="Fails intermittently on GitHub Actions' Windows runners",
)
@inlineCallbacks
def test_monitor_emits_file_modified_signal(magic_folder, tmp_path, qtbot):
    yield leave_all_folders(magic_folder)
    yield magic_folder.monitor.do_check()
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    with qtbot.wait_signal(magic_folder.monitor.file_modified) as blocker:
        yield magic_folder.add_folder(path, author)
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
        filepath.write_text(randstr() * 16)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert (blocker.args[0], blocker.args[1].get("relpath")) == (
        folder_name,
        filename,
    )


@inlineCallbacks
def test_monitor_emits_folder_status_changed_signal(
    magic_folder, tmp_path, qtbot
):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    with qtbot.wait_signal(
        magic_folder.monitor.folder_status_changed
    ) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert blocker.args[1] == MagicFolderStatus.SYNCING


@inlineCallbacks
def test_monitor_emits_overall_status_changed_signal(
    magic_folder, tmp_path, qtbot
):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author)
    with qtbot.wait_signal(
        magic_folder.monitor.overall_status_changed
    ) as blocker:
        filename = randstr()
        filepath = path / filename
        filepath.write_text(randstr() * 10)
        yield magic_folder.scan(folder_name)
        yield magic_folder.monitor.do_check()
    assert blocker.args[0] == MagicFolderStatus.SYNCING


def test_eliot_logs_collected(magic_folder):
    assert len(magic_folder.get_log_messages()) > 0
