import os

from pytest_twisted import inlineCallbacks

os.environ["PATH"] = (
    os.path.join(os.getcwd(), "dist", "Tahoe-LAFS")
    + os.pathsep
    + os.environ["PATH"]
)


@inlineCallbacks
def test_tahoe_client_connected_servers(tahoe_client):
    yield tahoe_client.await_ready()
    connected_servers = yield tahoe_client.get_connected_servers()
    assert connected_servers == 1


@inlineCallbacks
def test_tahoe_client_mkdir(tahoe_client):
    cap = yield tahoe_client.mkdir()
    assert cap.startswith("URI:DIR2:")


@inlineCallbacks
def test_diminish(tahoe_client):
    dircap = yield tahoe_client.mkdir()
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
    dircap = yield tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"1" * 64)
    local_path = p.resolve()
    cap = yield tahoe_client.upload(local_path, dircap)
    assert cap.startswith("URI:CHK:")


@inlineCallbacks
def test_ls(tahoe_client, tmp_path):
    dircap = yield tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield tahoe_client.mkdir()
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap)
    assert ("TestFile.txt" in output) and ("subdir" in output)


@inlineCallbacks
def test_ls_exclude_dirnodes(tahoe_client, tmp_path):
    dircap = yield tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield tahoe_client.mkdir()
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap, exclude_dirnodes=True)
    assert ("TestFile.txt" in output) and ("subdir" not in output)


@inlineCallbacks
def test_ls_exclude_filenodes(tahoe_client, tmp_path):
    dircap = yield tahoe_client.mkdir()
    p = tmp_path / "TestFile.txt"
    p.write_bytes(b"2" * 64)
    local_path = p.resolve()
    yield tahoe_client.upload(local_path, dircap)
    subdircap = yield tahoe_client.mkdir()
    yield tahoe_client.link(dircap, "subdir", subdircap)
    output = yield tahoe_client.ls(dircap, exclude_filenodes=True)
    assert ("TestFile.txt" not in output) and ("subdir" in output)
