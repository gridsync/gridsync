import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pytest_twisted import ensureDeferred, inlineCallbacks
from twisted.internet.defer import Deferred

from gridsync import APP_NAME
from gridsync.errors import TahoeWebError

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


@inlineCallbacks
def test_tahoe_client_mkdir_with_known_private_key(tahoe_client) -> None:
    private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQClHWyI+26yYVsh
B21ra4aPF24EekXlz5UponznP7gzSyZ2oxLEmyPsfLRGGPL1Qmir+ujYm+frAi0B
RmtW5pwNmLGFyBpeT4RSIjGaAVHYSstp07MRmulJFb/hij27CEzTkHWZ47Qt7m0L
Q65kU7RzpyHKAm3GaCH5POHfOJiW7p8a/0hWoqHrxuZ+akVjm2+h1P6Jgmo0f29j
uL/hSxgzJqaDkkaV3+2YEEQPtxiVNBwbLJhZdxX9sZhYlIccX6qIetDOMbqi5V5i
2vgE/QPQxjcAxMP83L7rXVFmxDZ4+FNLJAPuiW52630g7Z/TwHgZDlyKJJwfU75L
NSR2J9/rAgMBAAECggEAEQBCmKgq8bsMgw4cuh7MMBedgGCGqe8B0NOmQLlS4hUu
1LBd0liXDlaYyU7wVUiNNogTSZpj+tKyh5sUmlIMZ2n9fWTpMiTF3x8eNFlGcBrj
bvYZTgrBUoEmzLZLPOLR5kbNlRbZCpGuMKa7YiEsR2xCEmbFntRCC0O1jiJps8Cb
nbzXvQhy2PHkxPlX7ZoCgyWpAZlhylsUFPfw7DeuIiloLinaxEsYmli8BpK/JWPi
xUsaKVoEcBtrzOER3sTP5/h8zGbF/yxKC9PUCvShEFeK/boylC3/cCRReZlNANxV
Zh04nCwvgYUS/Lzd9/0N5lmA7GYF+z7+cLkz85bswQKBgQDi7NhB0N9HXevfUoTt
/DVrgx8HDCIzcl7xn02Bvv20i/j4ItGQzl3Fjou4uoxRI+z99CO9gPBUCXCkcQS/
2Dr8k31LMNTh+dPO55L2rtEN93bu/vakCLwWWQ5w4XLS16TVRaGu2vr6pV5fj3A3
d9DCHVrjd85OfThzMOHPwQRHMwKBgQC6RTNpseo0t0E92Azp4aJoYcb08CiycYPy
KB3uTuS+yLt6MVR6XTa0C+UeQGySoPavVMqomYs+AQGGe3vLhXH4SL2bR/HFxQ4s
/gR7Y4AHQ1vm1veKZBihW7AWKsU5+BNeXWyHZ3F7Ca0df+R+e2KqK19uh2ATnfjv
J2Oxsw6kaQKBgQCJ+AKMEZiPZZVRlHRp1ZwNIA2vVTs+GF2NfpO7PQo3yZq4E0Nj
TXVJ9h8RU6qYcsVWqidIwqpcDdlEwcpncep7Qpk9LBVix2h2Nenuvd8xJLJVIQOI
PB9PXxoem5QaiS4Y1Vs2WsGZvw2gAC/0KY7tVre58U+n/Q5jSucgT3RwbQKBgG7F
xINwuLVM3dGncFaORoUI0MbNI4arFyqlTNdxt3r16PgL6g8y69s6z7Cj4213p/ww
0qxdU382HfAZ807fNx3ONGPp7xAL1hhPn965F2Q6XKb05BU63aLn4dns6YlFzE7s
BCSqEcR3xqmqavoE6nIEhSY3/5zq7yVaKWF9+JExAoGBAIpzIT8VV10PZBcr/+EI
r4N1D1wu64vejommwIn/p6O8bg8yuJoqRWO2CjgCm/xHiztuUaYjY8E7P1YPBlQB
HCO87WjVqfwNmf2UssW56KAl2JhbzfPON3Ly8NJb18olcUEIO/hO5EC1GFsjD+hv
PQsRxG8N63MKqpMr0RNAFnRv
-----END PRIVATE KEY-----
"""
    cap = yield Deferred.fromCoroutine(
        tahoe_client.mkdir(private_key=private_key)
    )
    assert cap == (
        "URI:DIR2:cfublgatjhvsnssq5wzm3kmqx4:j2fie3fk63jianm52gz6wm3rdbvrd7qx5sy6z4fjjupiod5vqmuq"
    )


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
async def test_no_html_in_server_error(zkapauthorizer):
    try:
        # Attempting to create a directory using a `Tahoe` client that
        # is configured to use ZKAPAuthorizer against a `Tahoe` server
        # that is *not* configured to use ZKAPAuthorizer will fail with
        # a status code of 500 (possibly due to the mismatch in plugin
        # configurations between the client and the server -- or
        # possibly because the `Tahoe` client has no tokens yet?).
        # XXX: Maybe there's a better way to trigger a 500 error here?
        await zkapauthorizer.gateway.mkdir()
    except TahoeWebError as e:
        assert "status code 500:" in str(e) and "<!DOCTYPE html>" not in str(e)


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
