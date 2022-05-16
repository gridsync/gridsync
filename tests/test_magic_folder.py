from pathlib import Path

import pytest

from gridsync.crypto import randstr
from gridsync.magic_folder import (
    MagicFolder,
    MagicFolderConfigError,
    MagicFolderError,
    MagicFolderStatus,
)
from gridsync.tahoe import Tahoe


def test__read_api_token(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    magic_folder.configdir.mkdir(parents=True)
    api_token = randstr()
    Path(magic_folder.configdir / "api_token").write_text(api_token)
    assert magic_folder._read_api_token() == api_token


def test__read_api_token_raises_magic_folder_config_error_if_missing(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    with pytest.raises(MagicFolderConfigError):
        magic_folder._read_api_token()


def test__read_api_port(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    magic_folder.configdir.mkdir(parents=True)
    endpoint = "tcp:127.0.0.1:65536"
    Path(magic_folder.configdir / "api_client_endpoint").write_text(endpoint)
    assert magic_folder._read_api_port() == 65536


def test__read_api_port_raises_magic_folder_config_error_if_missing(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    with pytest.raises(MagicFolderConfigError):
        magic_folder._read_api_port()


def test__read_api_port_raises_magic_folder_error_if_not_running(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    magic_folder.configdir.mkdir(parents=True)
    endpoint = "not running"
    Path(magic_folder.configdir / "api_client_endpoint").write_text(endpoint)
    with pytest.raises(MagicFolderError):
        magic_folder._read_api_port()


def test__read_api_port_raises_magic_folder_config_error_if_not_int(tmp_path):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    magic_folder.configdir.mkdir(parents=True)
    endpoint = "tcp:127.0.0.1:NotAPort"
    Path(magic_folder.configdir / "api_client_endpoint").write_text(endpoint)
    with pytest.raises(MagicFolderConfigError):
        magic_folder._read_api_port()


@pytest.mark.parametrize(
    "state, status",
    [
        [
            {
                "synchronizing": False,
                "folders": {
                    "TestFolder": {
                        "uploads": [],
                        "downloads": [],
                        "errors": [],
                        "recent": [],
                        "tahoe": {"happy": True, "connected": 1, "desired": 1},
                        "scanner": {"last-scan": 1646062769.5709975},
                        "poller": {"last-poll": None},
                    },
                },
            },
            MagicFolderStatus.WAITING,
        ],
        [
            {
                "synchronizing": False,
                "folders": {
                    "TestFolder": {
                        "uploads": [
                            {
                                "relpath": "TestFile.txt",
                                "queued-at": 1646063072.4091136,
                                "started-at": 1646063073.829324,
                            },
                        ],
                        "downloads": [],
                        "errors": [],
                        "recent": [],
                        "tahoe": {"happy": True, "connected": 1, "desired": 1},
                        "scanner": {"last-scan": 1646062769.5709975},
                        "poller": {"last-poll": 1646062770.7937386},
                    },
                },
            },
            MagicFolderStatus.SYNCING,
        ],
        [
            {
                "synchronizing": False,
                "folders": {
                    "TestFolder": {
                        "uploads": [],
                        "downloads": [],
                        "errors": [{"timestamp": 1234567890, "summary": ":("}],
                        "recent": [],
                        "tahoe": {"happy": True, "connected": 1, "desired": 1},
                        "scanner": {"last-scan": 1646062769.5709975},
                        "poller": {"last-poll": 1646062770.7937386},
                    },
                },
            },
            MagicFolderStatus.ERROR,
        ],
        [
            {
                "synchronizing": False,
                "folders": {
                    "TestFolder": {
                        "uploads": [],
                        "downloads": [],
                        "errors": [],
                        "recent": [],
                        "tahoe": {"happy": True, "connected": 1, "desired": 1},
                        "scanner": {"last-scan": 1646062769.5709975},
                        "poller": {"last-poll": 1646062770.7937386},
                    },
                },
            },
            MagicFolderStatus.UP_TO_DATE,
        ],
    ],
)
def test_magic_folder_monitor__parse_folder_statuses(tmp_path, state, status):
    magic_folder = MagicFolder(Tahoe(tmp_path / "nodedir"))
    magic_folder.supervisor.time_started = 1  # XXX
    monitor = magic_folder.monitor
    statuses = monitor._parse_folder_statuses(state)
    assert statuses.get("TestFolder") == status
