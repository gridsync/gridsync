import os
import sys
from pathlib import Path

from pytest_twisted import inlineCallbacks
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


@inlineCallbacks
def test_tahoe_client_connected_servers(tahoe_client):
    yield tahoe_client.await_ready()
    connected_servers = yield Deferred.fromCoroutine(
        tahoe_client.get_connected_servers()
    )
    assert connected_servers == 1


@inlineCallbacks
def test_tahoe_client_mkdir(tahoe_client):
    cap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    assert cap.startswith("URI:DIR2:")


@inlineCallbacks
def test_diminish(tahoe_client):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    diminished = yield tahoe_client.diminish(dircap)
    assert diminished.startswith("URI:DIR2-RO:")


@inlineCallbacks
def test_upload_convergence_secret_determines_cap(tahoe_client, tmp_path):
    convergence_secret = tahoe_client.settings.get("convergence")
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"0" * 64)
    cap = yield tahoe_client.upload(p.resolve())
    assert (convergence_secret, cap) == (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "URI:CHK:rowlspe46wotpra7jruhtad3xy:"
        "lnviruztzbcugtpkrxnnodehpstlcoo6pswfgqjhv3teyn656fja:1:1:64",
    )


@inlineCallbacks
def test_upload_to_dircap(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap = yield tahoe_client.upload(local_path, dircap)
    assert cap.startswith("URI:CHK:")


@inlineCallbacks
def test_upload_mutable(tahoe_client, tmp_path):
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"0" * 64)
    local_path = p.resolve()
    cap = yield tahoe_client.upload(local_path, mutable=True)
    assert cap.startswith("URI:MDMF:")


@inlineCallbacks
def test_upload_to_dircap_mutable(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap = yield tahoe_client.upload(local_path, dircap, mutable=True)
    assert cap.startswith("URI:MDMF:")


@inlineCallbacks
def test_upload_to_dircap_mutable_uses_same_cap(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap1 = yield tahoe_client.upload(local_path, dircap, mutable=True)

    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    cap2 = yield tahoe_client.upload(local_path, dircap, mutable=True)
    assert cap2 == cap1


@inlineCallbacks
def test_ls(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap)
    assert ("TestFile.txt" in output) and ("subdir" in output)


@inlineCallbacks
def test_ls_exclude_dirnodes(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap, exclude_dirnodes=True)
    assert ("TestFile.txt" in output) and ("subdir" not in output)


@inlineCallbacks
def test_ls_exclude_filenodes(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap, exclude_filenodes=True)
    assert ("TestFile.txt" not in output) and ("subdir" in output)


@inlineCallbacks
def test_ls_includes_most_authoritative_cap(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    output = yield tahoe_client.ls(dircap)
    assert output.get("TestFile.txt").get("cap").startswith("URI:CHK:")


@inlineCallbacks
def test_ls_nonexistent_path(tahoe_client, tmp_path):
    dircap = yield Deferred.fromCoroutine(tahoe_client.mkdir())
    output = yield tahoe_client.ls(dircap + "/Path/Does/Not/Exist")
    assert output is None
