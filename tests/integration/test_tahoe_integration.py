import os
import sys
from pathlib import Path

from pytest_twisted import ensureDeferred, inlineCallbacks
from twisted.internet.defer import Deferred

from gridsync import APP_NAME

if sys.platform == "darwin":
    application_bundle_path = str(
        Path(
            os.getcwd(),
            "dist",
            APP_NAME + ".app",
            "Contents",
            "MacOS",
            "Tahoe-LAFS",
        ).resolve()
    )
else:
    application_bundle_path = str(
        Path(os.getcwd(), "dist", APP_NAME, "Tahoe-LAFS").resolve()
    )

os.environ["PATH"] = application_bundle_path + os.pathsep + os.environ["PATH"]


def test_tahoe_start_creates_pidfile(tahoe_client):
    assert Path(tahoe_client.pidfile).exists() is True


@ensureDeferred
async def test_tahoe_client_is_ready(tahoe_client):
    await tahoe_client.await_ready()
    ready = await tahoe_client.is_ready()
    assert ready is True


@inlineCallbacks
def test_tahoe_client_mkdir(tahoe_client):
    cap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    assert cap.startswith("URI:DIR2:")


@ensureDeferred
async def test_upload_convergence_secret_determines_cap(
    tahoe_client, tmp_path
):
    convergence_secret = tahoe_client.settings.get("convergence")
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"0" * 64)
    cap = await tahoe_client.upload(p.resolve())
    assert (convergence_secret, cap) == (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "URI:CHK:rowlspe46wotpra7jruhtad3xy:"
        "lnviruztzbcugtpkrxnnodehpstlcoo6pswfgqjhv3teyn656fja:1:1:64",
    )


@ensureDeferred
async def test_upload_to_dircap(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap = await tahoe_client.upload(local_path, dircap)
    assert cap.startswith("URI:CHK:")


@ensureDeferred
async def test_upload_mutable(tahoe_client, tmp_path):
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"0" * 64)
    local_path = p.resolve()
    cap = await tahoe_client.upload(local_path, mutable=True)
    assert cap.startswith("URI:MDMF:")


@ensureDeferred
async def test_upload_to_dircap_mutable(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap = await tahoe_client.upload(local_path, dircap, mutable=True)
    assert cap.startswith("URI:MDMF:")


@ensureDeferred
async def test_upload_to_dircap_mutable_uses_same_cap(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap1 = await tahoe_client.upload(local_path, dircap, mutable=True)

    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    cap2 = await tahoe_client.upload(local_path, dircap, mutable=True)
    assert cap2 == cap1


@ensureDeferred
async def test_ls(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    await tahoe_client.upload(local_path, dircap)
    subdircap = await tahoe_client.mkdir()
    await tahoe_client.link(dircap, "subdir", subdircap)
    output = await tahoe_client.ls(dircap)
    assert ("TestFile.txt" in output) and ("subdir" in output)


@ensureDeferred
async def test_ls_exclude_dirnodes(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    await tahoe_client.upload(local_path, dircap)
    subdircap = await tahoe_client.mkdir()
    await tahoe_client.link(dircap, "subdir", subdircap)
    output = await tahoe_client.ls(dircap, exclude_dirnodes=True)
    assert ("TestFile.txt" in output) and ("subdir" not in output)


@ensureDeferred
async def test_ls_exclude_filenodes(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    await tahoe_client.upload(local_path, dircap)
    subdircap = await tahoe_client.mkdir()
    await tahoe_client.link(dircap, "subdir", subdircap)
    output = await tahoe_client.ls(dircap, exclude_filenodes=True)
    assert ("TestFile.txt" not in output) and ("subdir" in output)


@ensureDeferred
async def test_ls_includes_most_authoritative_cap(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    await tahoe_client.upload(local_path, dircap)
    output = await tahoe_client.ls(dircap)
    assert output.get("TestFile.txt").get("cap").startswith("URI:CHK:")


@ensureDeferred
async def test_ls_nonexistent_path(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    output = await tahoe_client.ls(dircap + "/Path/Does/Not/Exist")
    assert output is None


@ensureDeferred
async def test_get_cap(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    subdircap = await tahoe_client.mkdir(dircap, "TestSubdir")
    output = await tahoe_client.get_cap(dircap + "/TestSubdir")
    assert output == subdircap


@ensureDeferred
async def test_get_cap_returns_none_for_missing_path(tahoe_client, tmp_path):
    dircap = await tahoe_client.mkdir()
    await tahoe_client.mkdir(dircap, "TestSubdir")
    output = await tahoe_client.get_cap(dircap + "/TestNonExistentSubdir")
    assert output is None


# XXX Run this test last since it modifies the nodedir that corresponds
# to the module-scoped `tahoe_client` fixture; we don't want the other
# tests in this module to be impacted by this shared state-modification
def test_apply_connection_settings(tahoe_client, tahoe_server):
    settings = {
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "2",
        "storage": {
            "test-grid-storage-server-2": {
                "nickname": "test-grid-storage-server-1",
                "anonymous-storage-FURL": tahoe_server.storage_furl,
            }
        },
    }
    tahoe_client.apply_connection_settings(settings)
    assert tahoe_client.config_get("client", "shares.total") == "2"
    storage_servers = tahoe_client.get_storage_servers()
    assert "test-grid-storage-server-2" in storage_servers
    assert "test-grid-storage-server-1" not in storage_servers
