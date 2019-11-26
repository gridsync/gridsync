# -*- coding: utf-8 -*-

import json
import os
from unittest.mock import MagicMock, Mock

import pytest
from pytest_twisted import inlineCallbacks
import yaml

from gridsync import resource
from gridsync.errors import UpgradeRequiredError, TorError
from gridsync.setup import (
    is_onion_grid,
    prompt_for_grid_name,
    validate_grid,
    prompt_for_folder_name,
    validate_folders,
    validate_settings,
    SetupRunner,
)
from gridsync.tahoe import Tahoe


@pytest.mark.parametrize(
    "settings,result",
    [
        [
            {
                "introducer": "pb://a@example.org:9999/b",
                "storage": {
                    "v0-aaaaaaaa": {
                        "anonymous-storage-FURL": "pb://a@1.example.org:9999/b",
                        "nickname": "node-1",
                    }
                },
            },
            False,
        ],
        [
            {
                "introducer": "pb://a@example.onion:9999/b",
                "storage": {
                    "v0-aaaaaaaa": {
                        "anonymous-storage-FURL": "pb://a@1.example.org:9999/b",
                        "nickname": "node-1",
                    }
                },
            },
            True,
        ],
        [
            {
                "introducer": "pb://a@example.org:9999/b",
                "storage": {
                    "v0-aaaaaaaa": {
                        "anonymous-storage-FURL": "pb://a@1.example.onion:9999/b",
                        "nickname": "node-1",
                    }
                },
            },
            True,
        ],
    ],
)
def test_is_onion_grid(settings, result):
    assert is_onion_grid(settings) == result


def test_prompt_for_grid_name(monkeypatch):
    monkeypatch.setattr(
        "gridsync.setup.QInputDialog.getText",
        lambda a, b, c, d, e: ("NewGridName", 1),
    )
    assert prompt_for_grid_name("GridName") == ("NewGridName", 1)


def test_validate_grid_no_nickname(monkeypatch, tmpdir_factory):
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir_factory.mktemp("config_dir"))
    )
    monkeypatch.setattr(
        "gridsync.setup.prompt_for_grid_name", lambda x, y: ("NewGridName", 1)
    )
    assert validate_grid({"nickname": None}) == {"nickname": "NewGridName"}


def test_validate_grid_conflicting_introducer(monkeypatch, tmpdir_factory):
    config_dir = str(tmpdir_factory.mktemp("config_dir"))
    monkeypatch.setattr("gridsync.setup.config_dir", config_dir)
    nodedir = os.path.join(config_dir, "ExistingGrid")
    os.makedirs(nodedir)
    with open(os.path.join(nodedir, "tahoe.cfg"), "w") as f:
        f.write("[client]\nintroducer.furl = pb://11111\n")
    monkeypatch.setattr(
        "gridsync.setup.prompt_for_grid_name", lambda x, y: ("NewGridName", 1)
    )
    settings = {"nickname": "ExistingGrid", "introducer": "pb://22222"}
    assert validate_grid(settings) == {
        "nickname": "NewGridName",
        "introducer": "pb://22222",
    }


def test_validate_grid_conflicting_servers(monkeypatch, tmpdir_factory):
    config_dir = str(tmpdir_factory.mktemp("config_dir"))
    monkeypatch.setattr("gridsync.setup.config_dir", config_dir)
    private_dir = os.path.join(config_dir, "ExistingGrid", "private")
    os.makedirs(private_dir)
    servers = {
        "storage": {
            "v0-aaaaaaaa": {
                "ann": {
                    "anonymous-storage-FURL": "pb://11111111",
                    "nickname": "node-1",
                }
            }
        }
    }
    with open(os.path.join(private_dir, "servers.yaml"), "w") as f:
        f.write(yaml.safe_dump(servers, default_flow_style=False))
    monkeypatch.setattr(
        "gridsync.setup.prompt_for_grid_name", lambda x, y: ("NewGridName", 1)
    )
    settings = {
        "nickname": "ExistingGrid",
        "storage": {
            "anonymous-storage-FURL": "pb://11111111",
            "nickname": "node-1",
        },
    }
    assert validate_grid(settings) == {
        "nickname": "NewGridName",
        "storage": {
            "anonymous-storage-FURL": "pb://11111111",
            "nickname": "node-1",
        },
    }


def test_prompt_for_folder_name(monkeypatch):
    monkeypatch.setattr(
        "gridsync.setup.QInputDialog.getText",
        lambda a, b, c, d, e: ("NewFolderName", 1),
    )
    assert prompt_for_folder_name("FolderName", "Grid") == ("NewFolderName", 1)


def test_validate_folders_no_known_gateways():
    assert validate_folders({}, []) == {}


def test_validate_folders_skip_folder(monkeypatch, tmpdir_factory):
    gateway = Tahoe(
        os.path.join(str(tmpdir_factory.mktemp("config_dir")), "SomeGrid")
    )
    gateway.magic_folders = {"FolderName": {}}
    monkeypatch.setattr(
        "gridsync.setup.prompt_for_folder_name", lambda x, y, z: (None, 0)
    )
    settings = {
        "nickname": "SomeGrid",
        "magic-folders": {"FolderName": {"code": "aaaaaaaa+bbbbbbbb"}},
    }
    assert validate_folders(settings, [gateway]) == {
        "nickname": "SomeGrid",
        "magic-folders": {},
    }


def test_validate_folders_rename_folder(monkeypatch, tmpdir_factory):
    gateway = Tahoe(
        os.path.join(str(tmpdir_factory.mktemp("config_dir")), "SomeGrid")
    )
    gateway.magic_folders = {"FolderName": {}}
    monkeypatch.setattr(
        "gridsync.setup.prompt_for_folder_name",
        lambda x, y, z: ("NewFolderName", 1),
    )
    settings = {
        "nickname": "SomeGrid",
        "magic-folders": {"FolderName": {"code": "aaaaaaaa+bbbbbbbb"}},
    }
    assert validate_folders(settings, [gateway]) == {
        "nickname": "SomeGrid",
        "magic-folders": {"NewFolderName": {"code": "aaaaaaaa+bbbbbbbb"}},
    }


def fake_validate(settings, *args):
    return settings


def test_validate_settings_strip_rootcap(monkeypatch):
    monkeypatch.setattr("gridsync.setup.validate_grid", fake_validate)
    settings = {"nickname": "SomeGrid", "rootcap": "URI:ROOTCAP"}
    assert validate_settings(settings, [], None) == {"nickname": "SomeGrid"}


def test_validate_settings_validate_folders(monkeypatch):
    monkeypatch.setattr("gridsync.setup.validate_grid", fake_validate)
    monkeypatch.setattr("gridsync.setup.validate_folders", fake_validate)
    settings = {
        "nickname": "SomeGrid",
        "magic-folders": {"NewFolderName": {"code": "aaaaaaaa+bbbbbbbb"}},
    }
    assert validate_settings(settings, [], None) == settings


def test_get_gateway_no_gateways():
    sr = SetupRunner([])
    assert not sr.get_gateway("pb://test", {})


@pytest.fixture(scope="module")
def fake_gateway():
    gateway = MagicMock()
    gateway.config_get.return_value = "pb://introducer"
    gateway.get_storage_servers.return_value = {"Test": {}}
    return gateway


def test_get_gateway_match_from_introducer(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert sr.get_gateway("pb://introducer", {}) == fake_gateway


def test_get_gateway_match_from_servers(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert sr.get_gateway(None, {"Test": {}}) == fake_gateway


def test_get_gateway_no_match(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert not sr.get_gateway("pb://test", {})


def test_calculate_total_steps_1_already_joined_grid(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {"introducer": "pb://introducer"}
    assert sr.calculate_total_steps(settings) == 1


def test_calculate_total_steps_5_need_to_join_grid(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {"introducer": "pb://introducer.other"}
    assert sr.calculate_total_steps(settings) == 5


def test_calculate_total_steps_6_need_to_join_grid_and_1_folder(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {
        "introducer": "pb://introducer.other",
        "magic-folders": {"FolderOne": {"code": "URI+URI"}},
    }
    assert sr.calculate_total_steps(settings) == 6


def test_calculate_total_steps_7_need_to_join_grid_and_2_folders(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {
        "introducer": "pb://introducer.other",
        "magic-folders": {
            "FolderOne": {"code": "URI+URI"},
            "FolderTwo": {"code": "URI+URI"},
        },
    }
    assert sr.calculate_total_steps(settings) == 7


def test_decode_icon_b64decode(tmpdir):
    sr = SetupRunner([])
    data = b"dGVzdDEyMzQ1"  # b64encode(b'test12345')
    dest = str(tmpdir.join("icon.png"))
    sr.decode_icon(data, dest)
    with open(dest) as f:
        assert f.read() == "test12345"


def test_decode_icon_emit_got_icon_signal(qtbot, tmpdir):
    sr = SetupRunner([])
    data = b"dGVzdDEyMzQ1"  # b64encode(b'test12345')
    dest = str(tmpdir.join("icon.png"))
    with qtbot.wait_signal(sr.got_icon) as blocker:
        sr.decode_icon(data, dest)
    assert blocker.args == [dest]


def test_decode_icon_no_emit_got_icon_signal(qtbot, tmpdir):
    sr = SetupRunner([])
    data = b"0"  # raises binascii.Error
    dest = str(tmpdir.join("icon.png"))
    with qtbot.assert_not_emitted(sr.got_icon):
        sr.decode_icon(data, dest)


def fake_get(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_get_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


@inlineCallbacks
def test_fetch_icon(monkeypatch, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join("icon.png"))
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: b"0")
    yield sr.fetch_icon("http://example.org/icon.png", dest)
    with open(dest) as f:
        assert f.read() == "0"


@inlineCallbacks
def test_fetch_icon_use_tor(monkeypatch, tmpdir):
    sr = SetupRunner([], use_tor=True)
    dest = str(tmpdir.join("icon.png"))
    fake_tor_web_agent = MagicMock()

    def fake_tor(*args):
        tor = MagicMock()
        tor.web_agent.return_value = fake_tor_web_agent
        return tor

    kwargs_received = []

    def fake_treq_get(*args, **kwargs):
        response = MagicMock()
        response.code = 200
        kwargs_received.append(kwargs)
        return response

    monkeypatch.setattr("treq.get", fake_treq_get)
    monkeypatch.setattr("treq.content", lambda _: b"0")
    monkeypatch.setattr("gridsync.setup.get_tor", fake_tor)
    yield sr.fetch_icon("http://example.org/icon.png", dest)
    assert kwargs_received == [{"agent": fake_tor_web_agent}]


@inlineCallbacks
def test_fetch_icon_use_tor_raise_tor_error(monkeypatch, tmpdir):
    sr = SetupRunner([], use_tor=True)
    dest = str(tmpdir.join("icon.png"))
    monkeypatch.setattr("gridsync.setup.get_tor", lambda _: None)
    with pytest.raises(TorError):
        yield sr.fetch_icon("http://example.org/icon.png", dest)


@inlineCallbacks
def test_fetch_icon_emit_got_icon_signal(monkeypatch, qtbot, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join("icon.png"))
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: b"0")
    with qtbot.wait_signal(sr.got_icon) as blocker:
        yield sr.fetch_icon("http://example.org/icon.png", dest)
    assert blocker.args == [dest]


@inlineCallbacks
def test_fetch_icon_no_emit_got_icon_signal(monkeypatch, qtbot, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join("icon.png"))
    monkeypatch.setattr("treq.get", fake_get_code_500)
    with qtbot.assert_not_emitted(sr.got_icon):
        yield sr.fetch_icon("http://example.org/icon.png", dest)


@inlineCallbacks
def test_join_grid_emit_update_progress_signal(monkeypatch, qtbot, tmpdir):
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir.mkdir("config_dir"))
    )
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid"}
    with qtbot.wait_signal(sr.update_progress) as blocker:
        yield sr.join_grid(settings)
    assert blocker.args == ["Connecting to TestGrid..."]


@inlineCallbacks
def test_join_grid_emit_update_progress_signal_via_tor(
    monkeypatch, qtbot, tmpdir
):
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir.mkdir("config_dir"))
    )
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    sr = SetupRunner([], use_tor=True)
    settings = {"nickname": "TestGrid"}
    with qtbot.wait_signal(sr.update_progress) as blocker:
        yield sr.join_grid(settings)
    assert blocker.args == ["Connecting to TestGrid via Tor..."]


@inlineCallbacks
def test_join_grid_emit_got_icon_signal_nickname_least_authority_s4(
    monkeypatch, qtbot, tmpdir
):
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir.mkdir("config_dir"))
    )
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    sr = SetupRunner([])
    settings = {"nickname": "Least Authority S4"}
    with qtbot.wait_signal(sr.got_icon) as blocker:
        yield sr.join_grid(settings)
    assert blocker.args == [resource("leastauthority.com.icon")]


@inlineCallbacks
def test_join_grid_emit_got_icon_signal_icon_base64(
    monkeypatch, qtbot, tmpdir
):
    tmp_config_dir = str(tmpdir.mkdir("config_dir"))
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr("gridsync.setup.config_dir", tmp_config_dir)
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "icon_base64": "dGVzdDEyMzQ1"}
    with qtbot.wait_signal(sr.got_icon) as blocker:
        yield sr.join_grid(settings)
    assert blocker.args == [os.path.join(tmp_config_dir, ".icon.tmp")]


@inlineCallbacks
def test_join_grid_emit_got_icon_signal_icon_url(monkeypatch, qtbot, tmpdir):
    tmp_config_dir = str(tmpdir.mkdir("config_dir"))
    os.makedirs(os.path.join(tmp_config_dir, "TestGrid"))
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr("gridsync.setup.config_dir", tmp_config_dir)
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: b"0")
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "icon_url": "https://gridsync.io/icon"}
    with qtbot.wait_signal(sr.got_icon) as blocker:
        yield sr.join_grid(settings)
    assert blocker.args == [os.path.join(tmp_config_dir, ".icon.tmp")]


@inlineCallbacks
def test_join_grid_no_emit_icon_signal_exception(monkeypatch, qtbot, tmpdir):
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir.mkdir("config_dir"))
    )
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())
    monkeypatch.setattr("treq.get", fake_get)
    monkeypatch.setattr("treq.content", lambda _: b"0")
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.fetch_icon",
        MagicMock(side_effect=Exception()),
    )
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "icon_url": "https://gridsync.io/icon"}
    with qtbot.assert_not_emitted(sr.got_icon):
        yield sr.join_grid(settings)


@inlineCallbacks
def test_join_grid_storage_servers(monkeypatch, tmpdir):
    monkeypatch.setattr(
        "gridsync.setup.select_executable", lambda: (None, None)
    )
    monkeypatch.setattr(
        "gridsync.setup.config_dir", str(tmpdir.mkdir("config_dir"))
    )
    monkeypatch.setattr("gridsync.setup.Tahoe", MagicMock())

    def fake_add_storage_servers(*_):
        assert True

    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.add_storage_servers", fake_add_storage_servers
    )
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "storage": {"test": "test"}}
    yield sr.join_grid(settings)


@inlineCallbacks
def test_ensure_recovery_write_settings(tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    sr = SetupRunner([])
    sr.gateway = Tahoe(nodedir)
    settings = {"nickname": "TestGrid", "rootcap": "URI:test"}
    yield sr.ensure_recovery(settings)
    with open(os.path.join(nodedir, "private", "settings.json")) as f:
        assert json.loads(f.read()) == settings


@inlineCallbacks
def test_ensure_recovery_create_rootcap(monkeypatch, tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    monkeypatch.setattr("gridsync.tahoe.Tahoe.create_rootcap", lambda _: "URI")
    monkeypatch.setattr("gridsync.tahoe.Tahoe.upload", lambda x, y: "URI:2")

    def fake_link(_, dircap, name, childcap):
        assert (dircap, name, childcap) == ("URI", "settings.json", "URI:2")

    monkeypatch.setattr("gridsync.tahoe.Tahoe.link", fake_link)
    sr = SetupRunner([])
    sr.gateway = Tahoe(nodedir)
    sr.gateway.rootcap = "URI"
    settings = {"nickname": "TestGrid"}
    yield sr.ensure_recovery(settings)


@inlineCallbacks
def test_ensure_recovery_create_rootcap_pass_on_error(monkeypatch, tmpdir):
    nodedir = str(tmpdir.mkdir("TestGrid"))
    os.makedirs(os.path.join(nodedir, "private"))
    monkeypatch.setattr(
        "gridsync.tahoe.Tahoe.create_rootcap", MagicMock(side_effect=OSError())
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.upload", lambda x, y: "URI:2")

    def fake_link(_, dircap, name, childcap):
        assert (dircap, name, childcap) == ("URI", "settings.json", "URI:2")

    monkeypatch.setattr("gridsync.tahoe.Tahoe.link", fake_link)
    sr = SetupRunner([])
    sr.gateway = Tahoe(nodedir)
    sr.gateway.rootcap = "URI"
    settings = {"nickname": "TestGrid"}
    yield sr.ensure_recovery(settings)


@inlineCallbacks
def test_join_folders_emit_joined_folders_signal(monkeypatch, qtbot, tmpdir):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.link", lambda a, b, c, d: None)
    sr = SetupRunner([])
    sr.gateway = Tahoe(str(tmpdir.mkdir("TestGrid")))
    sr.gateway.rootcap = "URI:rootcap"
    folders_data = {"TestFolder": {"code": "URI:1+URI:2"}}
    with qtbot.wait_signal(sr.joined_folders) as blocker:
        yield sr.join_folders(folders_data)
    assert blocker.args == [["TestFolder"]]


@inlineCallbacks
def test_run_raise_upgrade_required_error():
    sr = SetupRunner([])
    with pytest.raises(UpgradeRequiredError):
        yield sr.run({"version": 9999})


@inlineCallbacks
def test_run_join_grid(monkeypatch):
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.get_gateway", lambda x, y, z: Mock()
    )

    def fake_join_grid(*_):
        assert True

    monkeypatch.setattr("gridsync.setup.SetupRunner.join_grid", fake_join_grid)
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.ensure_recovery", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_folders", lambda x, y: None
    )
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "magic-folders": {"TestFolder": {}}}
    yield sr.run(settings)


@inlineCallbacks
def test_run_join_grid_use_tor(monkeypatch):
    monkeypatch.setattr("gridsync.tor.get_tor", lambda _: "FakeTorObject")
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.get_gateway", lambda x, y, z: Mock()
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_grid", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.ensure_recovery", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_folders", lambda x, y: None
    )
    sr = SetupRunner([], use_tor=True)
    settings = {"nickname": "TestGrid", "magic-folders": {"TestFolder": {}}}
    yield sr.run(settings)
    assert settings["hide-ip"]


@inlineCallbacks
def test_run_join_grid_use_tor_raise_tor_error(monkeypatch):
    monkeypatch.setattr("gridsync.setup.get_tor_with_prompt", lambda _: None)
    sr = SetupRunner([], use_tor=True)
    settings = {"nickname": "TestGrid", "magic-folders": {"TestFolder": {}}}
    with pytest.raises(TorError):
        yield sr.run(settings)


@inlineCallbacks
def test_run_emit_grid_already_joined_signal(monkeypatch, qtbot):
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.get_gateway", lambda x, y, z: Mock()
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_grid", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.ensure_recovery", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_folders", lambda x, y: None
    )
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid"}
    with qtbot.wait_signal(sr.grid_already_joined) as blocker:
        yield sr.run(settings)
    assert blocker.args == ["TestGrid"]


@inlineCallbacks
def test_run_call_scan_rootcap_after_join_folders(monkeypatch):
    fake_gateway = Mock()
    fake_gateway.monitor.scan_rootcap = Mock()
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.get_gateway", lambda x, y, z: fake_gateway
    )
    monkeypatch.setattr("gridsync.setup.SetupRunner.join_grid", Mock())
    monkeypatch.setattr("gridsync.setup.SetupRunner.ensure_recovery", Mock())
    monkeypatch.setattr("gridsync.setup.SetupRunner.join_folders", Mock())
    sr = SetupRunner([])
    yield sr.run({"nickname": "TestGrid", "magic-folders": {"TestFolder": {}}})
    assert fake_gateway.monitor.scan_rootcap.call_count == 1


@inlineCallbacks
def test_run_emit_done_signal(monkeypatch, qtbot):
    fake_gateway = Mock()
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.get_gateway", lambda x, y, z: fake_gateway
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_grid", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.ensure_recovery", lambda x, y: None
    )
    monkeypatch.setattr(
        "gridsync.setup.SetupRunner.join_folders", lambda x, y: None
    )
    sr = SetupRunner([])
    settings = {"nickname": "TestGrid", "magic-folders": {"TestFolder": {}}}
    with qtbot.wait_signal(sr.done) as blocker:
        yield sr.run(settings)
    assert blocker.args == [fake_gateway]
