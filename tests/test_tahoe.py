# -*- coding: utf-8 -*-

import os
from pathlib import Path

try:
    from unittest.mock import MagicMock, Mock
except ImportError:
    from mock import Mock, MagicMock

import pytest
import yaml
from pytest_twisted import inlineCallbacks
from twisted.internet.testing import MemoryReactorClock

from gridsync.crypto import randstr
from gridsync.errors import TahoeCommandError, TahoeError, TahoeWebError
from gridsync.tahoe import (
    Tahoe,
    get_nodedirs,
    is_valid_furl,
    storage_options_to_config,
)
from gridsync.zkapauthorizer import PLUGIN_NAME as ZKAPAUTHZ_PLUGIN_NAME


def fake_get(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_get_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


def fake_put(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_put_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


def fake_post(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_post_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


def test_is_valid_furl():
    assert is_valid_furl("pb://abc234@example.org:12345/introducer")


def test_is_valid_furl_no_port():
    assert not is_valid_furl("pb://abc234@example.org/introducer")


def test_is_valid_furl_no_host_separator():
    assert not is_valid_furl("pb://abc234example.org:12345/introducer")


def test_is_valid_furl_invalid_char_in_connection_hint():
    assert not is_valid_furl("pb://abc234@exam/ple.org:12345/introducer")


def test_is_valid_furl_tub_id_not_base32():
    assert not is_valid_furl("pb://abc123@example.org:12345/introducer")


def test_get_nodedirs(tahoe, tmpdir_factory):
    basedir = str(tmpdir_factory.getbasetemp())
    assert tahoe.nodedir in get_nodedirs(basedir)


def test_get_nodedirs_empty(tahoe, tmpdir_factory):
    basedir = os.path.join(str(tmpdir_factory.getbasetemp()), "non-existent")
    assert get_nodedirs(basedir) == []


def test_raise_tahoe_error():
    with pytest.raises(TahoeError):
        raise TahoeError


def test_raise_tahoe_command_error():
    with pytest.raises(TahoeCommandError):
        raise TahoeCommandError


def test_raise_tahoe_web_error():
    with pytest.raises(TahoeWebError):
        raise TahoeWebError


def test_tahoe_default_nodedir():
    tahoe_client = Tahoe()
    assert tahoe_client.nodedir == os.path.join(
        os.path.expanduser("~"), ".tahoe"
    )


@pytest.mark.parametrize(
    "given,expected",
    [
        (123456, 123456),
        (0, 0),
        (None, 2000000),  # Default specified in gridsync.streamedlogs
    ],
)
def test_tahoe_set_streamedlogs_maxlen_from_config_txt(
    monkeypatch, given, expected
):
    monkeypatch.setattr(
        "gridsync.tahoe.global_settings", {"debug": {"log_maxlen": given}}
    )
    client = Tahoe()
    assert client.streamedlogs._buffer.maxlen == expected


def test_tahoe_load_newscap_from_global_settings(tahoe, monkeypatch):
    global_settings = {
        "news:{}".format(tahoe.name): {"newscap": "URI:NewscapFromSettings"}
    }
    monkeypatch.setattr("gridsync.tahoe.global_settings", global_settings)
    tahoe.load_newscap()
    assert tahoe.newscap == "URI:NewscapFromSettings"


def test_tahoe_load_newscap_from_newscap_file(tahoe):
    with open(os.path.join(tahoe.nodedir, "private", "newscap"), "w") as f:
        f.write("URI:NewscapFromFile")
    tahoe.load_newscap()
    assert tahoe.newscap == "URI:NewscapFromFile"


def test_config_get(tahoe):
    assert tahoe.config_get("node", "nickname") == "default"


def test_config_set(tahoe):
    tahoe.config_set("node", "nickname", "test")
    assert tahoe.config_get("node", "nickname") == "test"


def test_get_settings(tahoe):
    settings = tahoe.get_settings()
    nickname = settings["nickname"]
    icon_url = settings["icon_url"]
    assert (nickname, icon_url) == (tahoe.name, "test_url")


def test_get_settings_includes_convergence_secret(tahoe):
    secret = randstr()
    Path(tahoe.nodedir, "private", "convergence").write_text(secret)
    assert (
        tahoe.get_settings(include_secrets=True).get("convergence") == secret
    )


def test_get_settings_exclude_convergence_secret_by_default(tahoe):
    secret = randstr()
    Path(tahoe.nodedir, "private", "convergence").write_text(secret)
    assert secret not in tahoe.get_settings()


def test_save_settings_includes_convergence_secret(tahoe):
    secret = randstr()
    tahoe.save_settings({"convergence": secret})
    assert Path(tahoe.nodedir, "private", "convergence").read_text() == secret


def test_export(tahoe, tmpdir_factory):
    dest = os.path.join(str(tmpdir_factory.getbasetemp()), "settings.json")
    tahoe.export(dest)
    assert os.path.isfile(dest)


def test_get_storage_servers_empty(tahoe):
    assert tahoe.get_storage_servers() == {}


def test_get_storage_servers_non_empty(tahoe):
    data = {
        "storage": {
            "v0-aaa": {
                "ann": {
                    "anonymous-storage-FURL": "pb://a.a",
                    "nickname": "alice",
                }
            }
        }
    }
    with open(tahoe.servers_yaml_path, "w") as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))
    assert tahoe.get_storage_servers() == {
        "v0-aaa": {"anonymous-storage-FURL": "pb://a.a", "nickname": "alice"}
    }


def test_add_storage_server(tahoe):
    tahoe.add_storage_server("v0-bbb", "pb://b.b", "bob")
    assert tahoe.get_storage_servers().get("v0-bbb") == {
        "anonymous-storage-FURL": "pb://b.b",
        "nickname": "bob",
    }


def test_add_storage_servers(tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    client = Tahoe(nodedir)
    storage_servers = {
        "node-1": {"anonymous-storage-FURL": "pb://test", "nickname": "One"}
    }
    client.add_storage_servers(storage_servers)
    assert client.get_storage_servers() == storage_servers


def test_add_storage_servers_no_add_missing_furl(tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    client = Tahoe(nodedir)
    storage_servers = {"node-1": {"nickname": "One"}}
    client.add_storage_servers(storage_servers)
    assert client.get_storage_servers() == {}


def test_storage_options_to_config_unknown():
    """
    If a storage option name is unrecognized ``storage_options_to_config``
    returns ``None``.
    """
    assert (
        storage_options_to_config(
            {
                "name": "privatestorageio-imaginary-v1",
            }
        )
        is None
    )


# The name of the tahoe.cfg section where ZKAPAuthorizer client plugin config
# goes.
zkapauthz_plugin_section = f"storageclient.plugins.{ZKAPAUTHZ_PLUGIN_NAME}"


def test_storage_options_to_config_no_optional_values():
    """
    If some storage options have none of the optional configuration values
    then the resulting tahoe.cfg enables the ZKAPAuthorizer plugin but has
    none of the missing options.
    """
    config = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
        }
    )
    assert config["client"]["storage.plugins"] == ZKAPAUTHZ_PLUGIN_NAME
    zkapauthz = config[zkapauthz_plugin_section]
    assert "pass_value" not in zkapauthz
    assert "default-token-count" not in zkapauthz
    assert "allowed-public-keys" not in zkapauthz


def test_storage_options_to_config_pass_value():
    """
    If ``pass-value`` is present in the storage options then it is included in
    the resulting configuration's ZKAPAuthorizer client plugin section.
    """
    pass_value = 12345
    key = "pass-value"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: pass_value,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == pass_value


def test_storage_options_to_config_default_token_count():
    """
    If ``default-token-count`` is present in the storage options then it is
    included in the resulting configuration's ZKAPAuthorizer client plugin
    section.
    """
    default_token_count = 54321
    key = "default-token-count"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: default_token_count,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == default_token_count


def test_storage_options_to_config_allowed_public_keys():
    """
    If ``allowed-public-keys`` is present in the storage options then it is
    included in the resulting configuration's ZKAPAuthorizer client plugin
    section.
    """
    allowed_public_keys = "Key1,Key2,Key3,Key4"
    key = "allowed-public-keys"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: allowed_public_keys,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == allowed_public_keys


def test_storage_options_to_config_lease_crawl_interval_mean():
    """
    If ``lease.crawl-interval.mean`` is present in the storage options then it
    is included in the resulting configuration's ZKAPAuthorizer client plugin
    section.
    """
    mean = 234
    key = "lease.crawl-interval.mean"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: mean,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == mean


def test_storage_options_to_config_lease_crawl_interval_range():
    """
    If ``lease.crawl-interval.range`` is present in the storage options then it
    is included in the resulting configuration's ZKAPAuthorizer client plugin
    section.
    """
    range_ = 456
    key = "lease.crawl-interval.range"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: range_,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == range_


def test_storage_options_to_config_lease_min_time_remaining():
    """
    If ``lease.min-time-remaining`` is present in the storage options then it
    is included in the resulting configuration's ZKAPAuthorizer client plugin
    section.
    """
    min_time = 789
    key = "lease.min-time-remaining"
    zkapauthz = storage_options_to_config(
        {
            "name": ZKAPAUTHZ_PLUGIN_NAME,
            key: min_time,
        }
    )[zkapauthz_plugin_section]
    assert zkapauthz[key] == min_time


def test_add_storage_servers_writes_zkapauthorizer_allowed_public_keys(tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    client = Tahoe(nodedir)
    storage_servers = {
        "node-1": {
            "anonymous-storage-FURL": "pb://test",
            "nickname": "One",
            "storage-options": [
                {
                    "name": ZKAPAUTHZ_PLUGIN_NAME,
                    "allowed-public-keys": "Key1,Key2,Key3,Key4",
                }
            ],
        }
    }
    client.add_storage_servers(storage_servers)
    allowed_public_keys = client.config_get(
        f"storageclient.plugins.{ZKAPAUTHZ_PLUGIN_NAME}",
        "allowed-public-keys",
    )
    assert allowed_public_keys == "Key1,Key2,Key3,Key4"


@inlineCallbacks
def test_tahoe_create_client_nodedir_exists_error(tahoe):
    with pytest.raises(FileExistsError):
        yield tahoe.create_client()


@inlineCallbacks
def test_tahoe_create_client_args(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", mocked_command)
    yield tahoe.create_client(nickname="test_nickname")
    args = mocked_command.call_args[0][0]
    assert set(["--nickname", "test_nickname"]).issubset(set(args))


@inlineCallbacks
def test_tahoe_create_client_args_compat(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", mocked_command)
    yield tahoe.create_client(happy=7)
    args = mocked_command.call_args[0][0]
    assert set(["--shares-happy", "7"]).issubset(set(args))


@inlineCallbacks
def test_tahoe_create_client_args_hide_ip(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", mocked_command)
    settings = {"hide-ip": True}
    yield tahoe.create_client(**settings)
    args = mocked_command.call_args[0][0]
    assert "--hide-ip" in args


@inlineCallbacks
def test_tahoe_create_client_add_storage_servers(tmpdir, monkeypatch):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    monkeypatch.setattr(
        "os.path.exists", lambda _: False
    )  # suppress FileExistsError
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", lambda x, y: None)
    client = Tahoe(nodedir)
    storage_servers = {
        "node-1": {"anonymous-storage-FURL": "pb://test", "nickname": "One"}
    }
    settings = {"nickname": "TestGrid", "storage": storage_servers}
    yield client.create_client(**settings)
    assert client.get_storage_servers() == storage_servers


@inlineCallbacks
def test_tahoe_stop_kills_pid_in_pidfile(tahoe, monkeypatch):
    Path(tahoe.pidfile).write_text(str("4194305"), encoding="utf-8")
    fake_process = Mock()
    monkeypatch.setattr("gridsync.system.Process", fake_process)
    yield tahoe.stop()
    assert fake_process.call_args[0][0] == 4194305


@pytest.mark.parametrize("locked,call_count", [(True, 1), (False, 0)])
@inlineCallbacks
def test_tahoe_stop_locked(locked, call_count, tahoe, monkeypatch):
    lock = MagicMock()
    lock.locked = locked
    lock.acquire = MagicMock()
    lock.release = MagicMock()
    tahoe.rootcap_manager.lock = lock
    monkeypatch.setattr("os.path.isfile", lambda x: True)
    yield tahoe.stop()
    assert (lock.acquire.call_count, lock.release.call_count) == (
        call_count,
        call_count,
    )


@inlineCallbacks
def test_get_grid_status(tahoe, monkeypatch):
    json_content = b"""{
        "introducers": {
            "statuses": [
                "Connected to introducer.local:3456 via tcp"
            ]
        },
        "servers": [
            {
                "connection_status": "Trying to connect",
                "nodeid": "v0-aaaaaaaaaaaaaaaaaaaaaaaa",
                "last_received_data": null,
                "version": null,
                "available_space": null,
                "nickname": "node1"
            },
            {
                "connection_status": "Connected to tcp:node2:4567 via tcp",
                "nodeid": "v0-bbbbbbbbbbbbbbbbbbbbbbbb",
                "last_received_data": 1509126406.799392,
                "version": "tahoe-lafs/1.12.1",
                "available_space": 1024,
                "nickname": "node2"
            },
            {
                "connection_status": "Connected to tcp:node3:5678 via tcp",
                "nodeid": "v0-cccccccccccccccccccccccc",
                "last_received_data": 1509126406.799392,
                "version": "tahoe-lafs/1.12.1",
                "available_space": 2048,
                "nickname": "node3"
            }
        ]
    }"""
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: json_content)
    num_connected, num_known, available_space = yield tahoe.get_grid_status()
    assert (num_connected, num_known, available_space) == (2, 3, 3072)


@inlineCallbacks
def test_get_connected_servers(tahoe, monkeypatch):
    html = b"Connected to <span>3</span>of <span>10</span>"
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: html)
    output = yield tahoe.get_connected_servers()
    assert output == 3


@inlineCallbacks
def test_is_ready_false_not_shares_happy(tahoe, monkeypatch):
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_is_ready_false_not_connected_servers(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers", lambda _: None
    )
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_is_ready_true(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers", lambda _: 10
    )
    output = yield tahoe.is_ready()
    assert output is True


@inlineCallbacks
def test_is_ready_false_connected_less_than_happy(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers", lambda _: 3
    )
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_await_ready(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.is_ready", lambda _: True)
    yield tahoe.await_ready()
    assert True


@inlineCallbacks
def test_concurrent_await_ready(tahoe, monkeypatch):
    """
    The rate of polling the Tahoe node for readiness is independent of the
    number of ``await_ready`` calls made.
    """
    # The tahoe fixture gets the mock reactor fixture which can't schedule
    # anything.  Replace it with a scheduler we control.
    clock = MemoryReactorClock()
    tahoe._ready_poller.clock = clock

    @inlineCallbacks
    def measure_poll_count(how_many_waiters):
        is_ready = False
        poll_count = 0

        def check_ready(self):
            nonlocal poll_count
            poll_count += 1
            return is_ready

        monkeypatch.setattr("gridsync.tahoe.Tahoe.is_ready", check_ready)

        # Start the polling operations
        waiters = [tahoe.await_ready() for n in range(how_many_waiters)]

        # Let some time pass.  This gives the poller some time to poll.
        clock.pump([0.1] * 10)

        # Mark the target as ready.
        is_ready = True

        # Let some time pass so the poller can notice.
        clock.pump([0.1] * 10)

        # All of the waiters should have their result.
        yield from waiters

        # Give back the counter we accumulated.
        return poll_count

    # Get the single caller rate
    single_count = yield measure_poll_count(1)

    # Then get the multi-caller rate
    multi_count = yield measure_poll_count(100)

    # Since we control the clock this measurement should be precise enough for
    # an exact equality comparison to be safe.  In practice, floating point
    # imprecision still means there's a little room for variation between the
    # two measurements.  This should be stable across runs but it might not be
    # stable across changes to the exact timing intervals used.  So allow it
    # to happen - or not.
    assert abs(multi_count - single_count) <= 1


@inlineCallbacks
def test_tahoe_mkdir(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post)
    monkeypatch.setattr("treq.content", lambda _: b"URI:DIR2:abc234:def567")
    output = yield tahoe.mkdir()
    assert output == "URI:DIR2:abc234:def567"


@inlineCallbacks
def test_tahoe_mkdir_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: b"test content")
    with pytest.raises(TahoeWebError):
        yield tahoe.mkdir()


@inlineCallbacks
def test_tahoe_upload(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.mkdir", lambda _: "URI:DIR2:abc")
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.put", fake_put)
    monkeypatch.setattr("treq.content", lambda _: b"test_cap")
    yield tahoe.create_rootcap()
    output = yield tahoe.upload(os.path.join(tahoe.nodedir, "tahoe.cfg"))
    assert output == "test_cap"


@inlineCallbacks
def test_tahoe_upload_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.mkdir", lambda _: "URI:DIR2:abc")
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.put", fake_put_code_500)
    monkeypatch.setattr("treq.content", lambda _: b"test content")
    yield tahoe.create_rootcap()
    with pytest.raises(TahoeWebError):
        yield tahoe.upload(os.path.join(tahoe.nodedir, "tahoe.cfg"))


@inlineCallbacks
def test_tahoe_download(tahoe, monkeypatch):
    def fake_collect(response, collector):
        collector(b"test_content")  # f.write(b'test_content')

    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.collect", fake_collect)
    location = os.path.join(tahoe.nodedir, "test_downloaded_file")
    yield tahoe.download("test_cap", location)
    with open(location, "r") as f:
        content = f.read()
        assert content == "test_content"


@inlineCallbacks
def test_tahoe_download_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.get", fake_get_code_500)
    monkeypatch.setattr("treq.content", lambda _: b"test content")
    with pytest.raises(TahoeWebError):
        yield tahoe.download("test_cap", os.path.join(tahoe.nodedir, "nofile"))


@inlineCallbacks
def test_tahoe_link(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post)
    yield tahoe.link("test_dircap", "test_childname", "test_childcap")
    assert True


@inlineCallbacks
def test_tahoe_link_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: b"test content")
    with pytest.raises(TahoeWebError):
        yield tahoe.link("test_dircap", "test_childname", "test_childcap")


@inlineCallbacks
def test_tahoe_unlink(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post)
    yield tahoe.unlink("test_dircap", "test_childname")
    assert True


@inlineCallbacks
def test_tahoe_unlink_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", MagicMock())
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: b"test content")
    with pytest.raises(TahoeWebError):
        yield tahoe.unlink("test_dircap", "test_childname")


@inlineCallbacks
def test_tahoe_start_use_tor_false(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp("tahoe-start")))
    client.magic_folder = Mock()  # XXX
    privatedir = os.path.join(client.nodedir, "private")
    os.makedirs(privatedir)
    nodeurl = "http://127.0.0.1:54321"
    client.set_nodeurl(nodeurl)
    with open(os.path.join(client.nodedir, "node.url"), "w") as f:
        f.write(nodeurl)
    with open(os.path.join(privatedir, "api_auth_token"), "w") as f:
        f.write("1234567890")
    client.config_set("client", "shares.happy", "99999")
    monkeypatch.setattr("shutil.which", lambda _: "_tahoe")
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: (9999, "tahoe"),
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins", lambda _: None
    )
    yield client.start()
    assert not client.use_tor


@inlineCallbacks
def test_tahoe_starts_streamedlogs(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: (9999, "tahoe"),
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins", lambda _: None
    )
    reactor = MemoryReactorClock()
    tahoe = tahoe_factory(reactor)
    tahoe.monitor = Mock()
    tahoe.config_set("client", "shares.needed", "3")
    tahoe.config_set("client", "shares.happy", "7")
    tahoe.config_set("client", "shares.total", "10")
    yield tahoe.start()
    tahoe._on_started()  # XXX
    assert tahoe.streamedlogs.running
    (host, port, _, _, _) = reactor.tcpClients.pop(0)
    assert (host, port) == ("example.invalid", 12345)


@inlineCallbacks
def test_tahoe_stops_streamedlogs(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: (9999, "tahoe"),
    )
    monkeypatch.setattr("gridsync.supervisor.Supervisor.stop", Mock())
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins", lambda _: None
    )
    tahoe = tahoe_factory(MemoryReactorClock())
    tahoe.monitor = Mock()
    tahoe.config_set("client", "shares.needed", "3")
    tahoe.config_set("client", "shares.happy", "7")
    tahoe.config_set("client", "shares.total", "10")
    yield tahoe.start()
    Path(tahoe.pidfile).write_text(str("4194306"), encoding="utf-8")
    yield tahoe.stop()
    assert not tahoe.streamedlogs.running


@inlineCallbacks
def test_tahoe_start_use_tor_true(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp("tahoe-start")))
    client.magic_folder = Mock()  # XXX
    privatedir = os.path.join(client.nodedir, "private")
    os.makedirs(privatedir)
    nodeurl = "http://127.0.0.1:54321"
    client.set_nodeurl(nodeurl)
    with open(os.path.join(client.nodedir, "node.url"), "w") as f:
        f.write(nodeurl)
    with open(os.path.join(privatedir, "api_auth_token"), "w") as f:
        f.write("1234567890")
    client.config_set("client", "shares.happy", "99999")
    client.config_set("connections", "tcp", "tor")
    monkeypatch.setattr("shutil.which", lambda _: "_tahoe")
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: (9999, "tahoe"),
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins", lambda _: None
    )
    yield client.start()
    assert client.use_tor
