import os
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from deterministic_keygen import derive_rsa_key
from pytest_twisted import ensureDeferred, inlineCallbacks
from twisted.internet.defer import Deferred

from gridsync import APP_NAME
from gridsync.tahoe import TahoeWebError

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


@inlineCallbacks
def test_tahoe_client_mkdir_with_random_private_key(tahoe_client) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    cap = yield Deferred.fromCoroutine(
        tahoe_client.mkdir(private_key=private_key_pem)
    )
    assert cap.startswith("URI:DIR2:")


@pytest.mark.parametrize(
    "input, expected",
    [
        [
            b"0" * 32,
            "URI:DIR2:qipxsqshywakqfgpfs75wr5wgm:xaesekzxu27ziew5n47sckyyjvdczd6kmbt22vldp633qwlrzjwq",
        ],
        [
            b"1" * 32,
            "URI:DIR2:zuyypcedyl6aw2swd7uqmtgmpi:m35xlt7gs5fi7tnuioztn5gtygyhyd3o2ctshucy5qahhbhwnyeq",
        ],
        [
            b"2" * 32,
            "URI:DIR2:gvbrggubcdghip6gjzzjqhj4yi:sct2pk6sqn2ilpu5netof4xhhm25lrcroag3bjeweeanb4m4o6uq",
        ],
    ],
)
@inlineCallbacks
def test_tahoe_client_mkdir_with_known_private_key(
    tahoe_client, input, expected
) -> None:
    private_key_pem = derive_rsa_key(input)
    cap = yield Deferred.fromCoroutine(
        tahoe_client.mkdir(private_key=private_key_pem)
    )
    assert cap == expected


@ensureDeferred
async def test_tahoe_client_mkdir_with_uncoordinated_write_error(
    tahoe_client, tmp_path
) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    # Creat a dircap using the given private key
    dircap = await Deferred.fromCoroutine(
        tahoe_client.mkdir(private_key=private_key_pem)
    )
    assert dircap.startswith("URI:DIR2:")

    # Upload a file beneath the dircap
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"test" * 64)
    filecap = await tahoe_client.upload(p.resolve(), dircap=dircap)

    # Get the directory contents
    contents_before = await tahoe_client.ls(dircap)
    assert "TestFile.txt" in contents_before
    assert contents_before["TestFile.txt"]["cap"] == filecap

    # This should fail with an UncoordinatedWriteError
    try:
        await Deferred.fromCoroutine(
            tahoe_client.mkdir(private_key=private_key_pem)
        )
    except TahoeWebError as e:  # UncoordinatedWriteError
        print(e)
        assert "allmydata.mutable.common.UncoordinatedWriteError" in str(e)

    contents2 = await tahoe_client.ls(dircap)
    assert "TestFile.txt" in contents2
    assert contents2["TestFile.txt"]["cap"] == filecap


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


@ensureDeferred
async def test_load_vectors(tahoe_client) -> None:
    import yaml

    with open(Path(__file__).parent / "vectors" / "tahoe-lafs.yaml") as f:
        data = yaml.safe_load(f)
    for vector in data["vector"]:
        kind = vector["format"]["kind"]
        if kind == "ssk":
            key = vector["format"]["params"]["key"]
            expected = vector["expected"]
            expected_writekey = expected.split(":")[2]
            expected_fingerprint = expected.split(":")[3]

            cap = await tahoe_client.mkdir(private_key=key)
            actual_writekey = cap.split(":")[2]
            actual_fingerprint = cap.split(":")[3]

            assert actual_writekey == expected_writekey
            assert actual_fingerprint == expected_fingerprint
