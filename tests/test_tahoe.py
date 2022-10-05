# -*- coding: utf-8 -*-

import os
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

try:
    from unittest.mock import MagicMock, Mock
except ImportError:
    from mock import Mock, MagicMock

import pytest
import yaml
from pytest_twisted import ensureDeferred, inlineCallbacks
from twisted.internet.defer import Deferred, succeed
from twisted.internet.testing import MemoryReactorClock

from gridsync.crypto import randstr
from gridsync.errors import TahoeCommandError, TahoeError, TahoeWebError
from gridsync.tahoe import (
    Tahoe,
    get_nodedirs,
    has_legacy_magic_folder,
    has_legacy_zkapauthorizer,
    is_valid_furl,
    storage_options_to_config,
)
from gridsync.zkapauthorizer import PLUGIN_NAME as ZKAPAUTHZ_PLUGIN_NAME


def fake_get(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return succeed(response)


def fake_get_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return succeed(response)


def fake_put(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return succeed(response)


def fake_put_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return succeed(response)


def fake_post(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return succeed(response)


def fake_post_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return succeed(response)


async def noop_scan_storage_plugins(self):
    pass


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


@pytest.mark.parametrize(
    "contents, result",
    [
        ("[magic_folder]\nenabled = True", True),
        ("[magic_folder]\nenabled = False", True),
        ("[NOT_magic_folder]\nenabled = True", False),
        ("", False),
    ],
)
def test_has_legacy_magic_folder(tmp_path, contents, result):
    tahoe_cfg = tmp_path / "tahoe.cfg"
    tahoe_cfg.write_text(contents)
    assert has_legacy_magic_folder(tmp_path) == result


@pytest.mark.parametrize(
    "contents, result",
    [
        (
            "[client]\nstorage.plugins = privatestorageio-zkapauthz-v1\n",
            True,
        ),
        (
            "[client]\nstorage.plugins = privatestorageio-zkapauthz-v2\n",
            False,
        ),
        (
            "[storageclient.plugins.privatestorageio-zkapauthz-v1]\n"
            "redeemer = ristretto",
            True,
        ),
        (
            "[storageclient.plugins.privatestorageio-zkapauthz-v2]\n"
            "redeemer = ristretto",
            False,
        ),
    ],
)
def test_has_legacy_zkapauthorizer(tmp_path, contents, result):
    tahoe_cfg = tmp_path / "tahoe.cfg"
    tahoe_cfg.write_text(contents)
    assert has_legacy_zkapauthorizer(tmp_path) == result


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


def test_get_settings_includes_diminished_rootcap(tahoe):
    tahoe.rootcap_manager.set_rootcap(
        "URI:DIR2:x6ciqn3dbnkslpvazwz6z7ic2q:"
        "slkf7invl5apcabpyztxazkcufmptsclx7m3rn6hhiyuiz2hvu6a",
        overwrite=True,
    )
    settings = tahoe.get_settings(include_secrets=True)
    assert settings["rootcap"].startswith("URI:DIR2-RO:")


def test_get_settings_omits_rootcap_if_empty(tahoe):
    tahoe.rootcap_manager.set_rootcap("", overwrite=True)
    settings = tahoe.get_settings(include_secrets=True)
    assert "rootcap" not in settings


def test_get_settings_includes_convergence_secret(tahoe):
    secret = randstr()
    Path(tahoe.nodedir, "private", "convergence").write_text(secret)
    assert (
        tahoe.get_settings(include_secrets=True).get("convergence") == secret
    )


def test_get_settings_omits_convergence_secret_if_file_not_found(tahoe):
    Path(tahoe.nodedir, "private", "convergence").unlink(missing_ok=True)
    settings = tahoe.get_settings(include_secrets=True)
    assert "convergence" not in settings


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
        yield Deferred.fromCoroutine(tahoe.create_client({}))


def command_spy():
    intel = []

    async def spy(self, args) -> None:
        intel.append(args)

    return spy, intel


def has_args(actual: list[str], expected: tuple[str]) -> bool:
    """
    :return: ``True`` if the expected argument tuple is present in the actual
        argument list.
    """
    diff = len(actual) - len(expected)
    if diff < 0:
        return False
    for pos in range(diff):
        if tuple(actual[pos : pos + len(expected)]) == expected:
            return True
    return False


@inlineCallbacks
def test_tahoe_create_client_args(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    spy, intel = command_spy()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", spy)
    yield Deferred.fromCoroutine(
        tahoe.create_client({"nickname": "test_nickname"})
    )
    assert has_args(intel[0], ("--nickname", "test_nickname"))


@inlineCallbacks
def test_tahoe_create_client_args_compat(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    spy, intel = command_spy()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", spy)
    yield Deferred.fromCoroutine(tahoe.create_client({"happy": "7"}))
    assert has_args(intel[0], ("--shares-happy", "7"))


@inlineCallbacks
def test_tahoe_create_client_args_hide_ip(tahoe, monkeypatch):
    monkeypatch.setattr("os.path.exists", lambda x: False)
    spy, intel = command_spy()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", spy)
    settings = {"hide-ip": True}
    yield Deferred.fromCoroutine(tahoe.create_client(settings))
    assert has_args(intel[0], ("--hide-ip",))


@inlineCallbacks
def test_tahoe_create_client_add_storage_servers(tmpdir, monkeypatch):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    monkeypatch.setattr(
        "os.path.exists", lambda _: False
    )  # suppress FileExistsError
    monkeypatch.setattr("gridsync.tahoe.Tahoe.command", command_spy()[0])
    client = Tahoe(nodedir)
    storage_servers = {
        "node-1": {"anonymous-storage-FURL": "pb://test", "nickname": "One"}
    }
    settings = {"nickname": "TestGrid", "storage": storage_servers}
    yield Deferred.fromCoroutine(client.create_client(settings))
    assert client.get_storage_servers() == storage_servers


@pytest.mark.parametrize("locked,call_count", [(True, 1), (False, 0)])
@ensureDeferred
async def test_tahoe_stop_locked(locked, call_count, tahoe, monkeypatch):
    monkeypatch.setattr("os.path.isfile", lambda x: True)

    events: list[str] = []

    if locked:
        await tahoe.rootcap_manager.lock.acquire()
        from twisted.internet import reactor
        from twisted.internet.task import deferLater

        def unlock():
            events.append("unlocking")
            tahoe.rootcap_manager.lock.release()

        d = deferLater(reactor, 0.0, unlock)
    else:
        d = succeed(None)

    await tahoe.stop()
    events.append("stopped")
    await d

    if locked:
        assert events == ["unlocking", "stopped"]

    assert not tahoe.rootcap_manager.lock.locked


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
    monkeypatch.setattr("treq.content", lambda _: succeed(json_content))
    num_connected, num_known, available_space = yield Deferred.fromCoroutine(
        tahoe.get_grid_status()
    )
    assert (num_connected, num_known, available_space) == (2, 3, 3072)


@inlineCallbacks
def test_get_connected_servers(tahoe, monkeypatch):
    html = b"Connected to <span>3</span>of <span>10</span>"
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: succeed(html))
    output = yield Deferred.fromCoroutine(tahoe.get_connected_servers())
    assert output == 3


@inlineCallbacks
def test_is_ready_false_not_shares_happy(tahoe, monkeypatch):
    output = yield Deferred.fromCoroutine(tahoe.is_ready())
    assert output is False


T = TypeVar("T")


def fake_awaitable_method(value: T) -> Callable[[], Awaitable[T]]:
    async def fake(self) -> T:
        return value

    return fake


@inlineCallbacks
def test_is_ready_false_not_connected_servers(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers",
        fake_awaitable_method(None),
    )
    output = yield Deferred.fromCoroutine(tahoe.is_ready())
    assert output is False


@inlineCallbacks
def test_is_ready_true(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers",
        fake_awaitable_method(10),
    )
    output = yield Deferred.fromCoroutine(tahoe.is_ready())
    assert output is True


@inlineCallbacks
def test_is_ready_false_connected_less_than_happy(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.get_connected_servers",
        fake_awaitable_method(3),
    )
    output = yield Deferred.fromCoroutine(tahoe.is_ready())
    assert output is False


@inlineCallbacks
def test_await_ready(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.is_ready", fake_awaitable_method(True)
    )
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

        async def check_ready(self) -> bool:
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
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post)
    monkeypatch.setattr(
        "treq.content", lambda _: succeed(b"URI:DIR2:abc234:def567")
    )
    output = yield Deferred.fromCoroutine(tahoe.mkdir())
    assert output == "URI:DIR2:abc234:def567"


@inlineCallbacks
def test_tahoe_mkdir_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test content"))
    with pytest.raises(TahoeWebError):
        yield Deferred.fromCoroutine(tahoe.mkdir())


@ensureDeferred
async def test_tahoe_upload(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.mkdir", fake_awaitable_method("URI:DIR2:abc")
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.put", fake_put)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test_cap"))
    await tahoe.create_rootcap()
    output = await tahoe.upload(os.path.join(tahoe.nodedir, "tahoe.cfg"))
    assert output == "test_cap"


@ensureDeferred
async def test_tahoe_upload_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.mkdir", fake_awaitable_method("URI:DIR2:abc")
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.put", fake_put_code_500)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test content"))
    await tahoe.create_rootcap()
    with pytest.raises(TahoeWebError):
        await tahoe.upload(os.path.join(tahoe.nodedir, "tahoe.cfg"))


@inlineCallbacks
def test_tahoe_download(tahoe, monkeypatch):
    def fake_collect(response, collector):
        collector(b"test_content")  # f.write(b'test_content')
        return succeed(None)

    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.collect", fake_collect)
    location = os.path.join(tahoe.nodedir, "test_downloaded_file")
    yield Deferred.fromCoroutine(tahoe.download("test_cap", location))
    with open(location, "r") as f:
        content = f.read()
        assert content == "test_content"


@ensureDeferred
async def test_tahoe_download_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.get", fake_get_code_500)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test content"))
    with pytest.raises(TahoeWebError):
        await tahoe.download("test_cap", os.path.join(tahoe.nodedir, "nofile"))


@ensureDeferred
async def test_tahoe_link(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post)
    await tahoe.link("test_dircap", "test_childname", "test_childcap")
    assert True


@ensureDeferred
async def test_tahoe_link_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test content"))
    with pytest.raises(TahoeWebError):
        await tahoe.link("test_dircap", "test_childname", "test_childcap")


@ensureDeferred
async def test_tahoe_unlink(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post)
    await tahoe.unlink("test_dircap", "test_childname")
    assert True


@ensureDeferred
async def test_tahoe_unlink_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.await_ready", lambda _: succeed(None)
    )
    monkeypatch.setattr("treq.post", fake_post_code_500)
    monkeypatch.setattr("treq.content", lambda _: succeed(b"test content"))
    with pytest.raises(TahoeWebError):
        await tahoe.unlink("test_dircap", "test_childname")


@ensureDeferred
async def test_tahoe_start_use_tor_false(monkeypatch, tmpdir_factory):
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
        lambda *args, **kwargs: succeed((9999, "tahoe")),
    )

    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins",
        noop_scan_storage_plugins,
    )
    await client.start()
    assert not client.use_tor


@ensureDeferred
async def test_tahoe_starts_websocketreaderservice(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: succeed((9999, "tahoe")),
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins",
        noop_scan_storage_plugins,
    )
    reactor = MemoryReactorClock()
    tahoe = tahoe_factory(reactor)
    tahoe.monitor = Mock()
    tahoe.config_set("client", "shares.needed", "3")
    tahoe.config_set("client", "shares.happy", "7")
    tahoe.config_set("client", "shares.total", "10")
    await tahoe.start()
    tahoe._on_started()  # XXX
    assert tahoe._ws_reader.running
    (host, port, _, _, _) = reactor.tcpClients.pop(0)
    assert (host, port) == ("example.invalid", 12345)


@ensureDeferred
async def test_tahoe_stops_websocketreaderservice(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.start",
        lambda *args, **kwargs: succeed((9999, "tahoe")),
    )
    monkeypatch.setattr(
        "gridsync.supervisor.Supervisor.stop", lambda self: succeed(None)
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins",
        noop_scan_storage_plugins,
    )
    tahoe = tahoe_factory(MemoryReactorClock())
    tahoe.monitor = Mock()
    tahoe.config_set("client", "shares.needed", "3")
    tahoe.config_set("client", "shares.happy", "7")
    tahoe.config_set("client", "shares.total", "10")
    await tahoe.start()
    Path(tahoe.pidfile).write_text(str("4194306"), encoding="utf-8")
    await tahoe.stop()
    assert tahoe._ws_reader is None


@ensureDeferred
async def test_tahoe_start_use_tor_true(monkeypatch, tmpdir_factory):
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
        lambda *args, **kwargs: succeed((9999, "tahoe")),
    )
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.scan_storage_plugins",
        noop_scan_storage_plugins,
    )
    await client.start()
    assert client.use_tor
