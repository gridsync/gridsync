import errno
import socket
from random import randint

from pytest_twisted import async_yield_fixture, inlineCallbacks

from gridsync.tahoe import Tahoe


def get_free_port(
    port: int = 0, range_min: int = 49152, range_max: int = 65535
) -> int:
    if not port:
        port = randint(range_min, range_max)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except socket.error as err:
                if err.errno == errno.EADDRINUSE:
                    port = randint(range_min, range_max)
                    continue
                raise
            return port


@async_yield_fixture(scope="module")
async def tahoe_server(tmp_path_factory):
    server = Tahoe(tmp_path_factory.mktemp("tahoe_server") / "nodedir")
    print("Server nodedir:", server.nodedir)
    port = get_free_port()
    await server.create_node(
        port=f"tcp:{port}:interface=127.0.0.1",
        location=f"tcp:127.0.0.1:{port}",
    )
    await server.start()
    yield server
    await server.stop()


@async_yield_fixture(scope="module")
async def tahoe_client(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
    print("Client nodedir:", client.nodedir)
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
    yield client
    await client.stop()


@inlineCallbacks
def test_tahoe_client_connected_servers(tahoe_client):
    yield tahoe_client.await_ready()
    connected_servers = yield tahoe_client.get_connected_servers()
    assert connected_servers == 1


@inlineCallbacks
def test_tahoe_client_mkdir(tahoe_client):
    cap = yield tahoe_client.mkdir()
    assert cap.startswith("URI:DIR2:")
