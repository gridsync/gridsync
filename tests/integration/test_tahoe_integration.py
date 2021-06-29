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
