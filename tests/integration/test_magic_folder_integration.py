import os
import secrets
import string

from pytest_twisted import async_yield_fixture, inlineCallbacks

os.environ["PATH"] = (
    os.path.join(os.getcwd(), "dist", "magic-folder")
    + os.pathsep
    + os.environ["PATH"]
)


def randstr(length: int = 32, alphabet: str = "") -> str:
    if not alphabet:
        alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


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
def test_add_folder_and_get_folder(magic_folder, tmp_path):
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
    folder_was_added = (folder_name in folders)

    yield magic_folder.leave_folder(folder_name)
    folders = yield magic_folder.get_folders()
    folder_was_removed = (folder_name not in folders)

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
