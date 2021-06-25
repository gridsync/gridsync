import os

from pytest_twisted import async_yield_fixture, inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync.crypto import randstr

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
    yield magic_folder.restart()

    filename = randstr()
    filepath = path / filename
    filepath.write_text("Test" * 100)
    yield magic_folder.add_snapshot(folder_name, filename)
    snapshots = yield magic_folder.get_snapshots()
    assert filename in snapshots.get(folder_name)


@inlineCallbacks
def test_snapshot_uploads_to_personal_dmd(magic_folder, tmp_path):
    folder_name = randstr()
    path = tmp_path / folder_name
    author = randstr()
    yield magic_folder.add_folder(path, author, poll_interval=1)
    yield magic_folder.restart()

    filename = randstr()
    filepath = path / filename
    filepath.write_text("Test" * 100)
    yield magic_folder.add_snapshot(folder_name, filename)

    folders = yield magic_folder.get_folders()
    upload_dircap = folders[folder_name]["upload_dircap"]

    yield deferLater(reactor, 1, lambda: None)

    content = yield magic_folder.gateway.get_json(upload_dircap)
    assert filename in content[1]["children"]


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
