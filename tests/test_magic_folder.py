from pathlib import Path

import pytest

from gridsync.crypto import randstr
from gridsync.magic_folder import (
    MagicFolder,
    MagicFolderConfigError,
    MagicFolderError,
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
