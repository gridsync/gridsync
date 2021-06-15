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
