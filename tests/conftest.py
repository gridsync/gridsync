import os
import os.path
import sys
from base64 import b64encode
from functools import partial
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest_twisted import async_yield_fixture

from gridsync import APP_NAME
from gridsync.network import get_free_port
from gridsync.tahoe import Tahoe

if sys.platform == "darwin":
    application_bundle_path = str(
        Path(
            os.getcwd(),
            "dist",
            APP_NAME + ".app",
            "Contents",
            "MacOS",
        ).resolve()
    )
else:
    application_bundle_path = str(
        Path(os.getcwd(), "dist", APP_NAME).resolve()
    )

os.environ["PATH"] = application_bundle_path + os.pathsep + os.environ["PATH"]


@async_yield_fixture(scope="module")
async def tahoe_server(tmp_path_factory):
    server = Tahoe(tmp_path_factory.mktemp("tahoe_server") / "nodedir")
    port = get_free_port()
    await server.create_node(
        port=f"tcp:{port}:interface=127.0.0.1",
        location=f"tcp:127.0.0.1:{port}",
    )
    server.config_set("storage", "reserved_space", "10M")
    await server.start()
    yield server
    await server.stop()


@async_yield_fixture(scope="module")
async def tahoe_client(tmp_path_factory, tahoe_server):
    client = Tahoe(tmp_path_factory.mktemp("tahoe_client") / "nodedir")
    settings = {
        "nickname": "Test Grid",
        "shares-needed": "1",
        "shares-happy": "1",
        "shares-total": "1",
        "convergence": "a" * 52,
        "storage": {
            "test-grid-storage-server-1": {
                "nickname": "test-grid-storage-server-1",
                "anonymous-storage-FURL": tahoe_server.storage_furl,
            }
        },
    }
    await client.create_client(**settings)
    client.save_settings(settings)
    await client.start()
    yield client
    await client.stop()


@pytest.fixture()
def reactor():
    return Mock()


def _tahoe(tmpdir_factory, reactor):
    client = Tahoe(
        str(tmpdir_factory.mktemp("tahoe")),
        executable="tahoe_exe",
        reactor=reactor,
    )
    with open(os.path.join(client.nodedir, "tahoe.cfg"), "w") as f:
        f.write("[node]\nnickname = default")
    with open(os.path.join(client.nodedir, "icon.url"), "w") as f:
        f.write("test_url")
    private_dir = os.path.join(client.nodedir, "private")
    os.mkdir(private_dir)
    with open(os.path.join(private_dir, "aliases"), "w") as f:
        f.write("test_alias: test_cap")
    with open(os.path.join(private_dir, "magic_folders.yaml"), "w") as f:
        f.write("magic-folders:\n  test_folder: {directory: test_dir}")
    client.set_nodeurl("http://example.invalid:12345/")
    with open(os.path.join(client.nodedir, "node.url"), "w") as f:
        f.write("http://example.invalid:12345/")
    api_token = b64encode(b"a" * 32).decode("ascii")
    client.api_token = api_token
    with open(os.path.join(private_dir, "api_auth_token"), "w") as f:
        f.write(api_token)
    client.magic_folder = Mock()  # XXX
    return client


@pytest.fixture()
def tahoe_factory(tmpdir_factory):
    return partial(_tahoe, tmpdir_factory)


@pytest.fixture()
def tahoe(tmpdir_factory, reactor):
    return _tahoe(tmpdir_factory, reactor)


@pytest.fixture()
def fake_tahoe():
    t = Mock()
    t.name = "TestGrid"
    t.shares_happy = 3
    t.settings = {"zkap_payment_url_root": "https://example.invalid./"}
    t.zkapauthorizer = Mock()
    t.zkapauthorizer.zkap_unit_multiplier = 0.001
    t.zkapauthorizer.zkap_unit_name = "MB"
    t.zkapauthorizer.zkap_batch_size = 10000
    return t
