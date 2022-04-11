# -*- coding: utf-8 -*-

import os
import sys
from importlib import reload

import pytest

import gridsync
from gridsync import load_settings_from_cheatcode


def test_the_approval_of_RMS():  # :)
    assert gridsync.__license__.startswith("GPL")


def test___version__():
    assert gridsync.__version__


def test_pkgdir(monkeypatch):
    monkeypatch.setattr("sys.frozen", False, raising=False)
    assert gridsync.pkgdir == os.path.dirname(
        os.path.realpath(gridsync.__file__)
    )


def test_frozen_pkgdir(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    reload(gridsync)
    assert gridsync.pkgdir == os.path.dirname(os.path.realpath(sys.executable))


@pytest.mark.xfail(strict=False)
# XXX/FIXME: Failing on fresh CentOS-7 environment; look into this later...
def test_append_tahoe_bundle_to_PATH(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    old_path = os.environ["PATH"]
    reload(gridsync)
    modified_path = os.environ["PATH"]
    tahoe_dir = os.pathsep + os.path.join(gridsync.pkgdir, "Tahoe-LAFS")
    assert modified_path != old_path and modified_path.endswith(tahoe_dir)


def test_frozen_del_reactor(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    sys.modules["twisted.internet.reactor"] = "test"
    reload(gridsync)
    assert "twisted.internet.reactor" not in sys.modules


def test_frozen_del_reactor_pass_without_twisted(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    reload(gridsync)
    assert "twisted.internet.reactor" not in sys.modules


def test_override_settings_via_environment_variables():
    os.environ["GRIDSYNC_APPLICATION_NAME"] = "TestApp"
    reload(gridsync)
    assert gridsync.settings["application"]["name"] == "TestApp"


def test_add_settings_via_environment_variables():
    os.environ["GRIDSYNC_TEST_SETTING_X"] = "123"
    reload(gridsync)
    assert gridsync.settings["test"]["setting_x"] == "123"


def test_config_dir_win32(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", "C:\\Users\\test\\AppData\\Roaming")
    reload(gridsync)
    assert gridsync.config_dir == os.path.join(
        os.getenv("APPDATA"), gridsync.APP_NAME
    )


def test_config_dir_darwin(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    reload(gridsync)
    assert gridsync.config_dir == os.path.join(
        os.path.expanduser("~"),
        "Library",
        "Application Support",
        gridsync.APP_NAME,
    )


def test_config_dir_other(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    reload(gridsync)
    assert gridsync.config_dir == os.path.join(
        os.path.expanduser("~"), ".config", gridsync.APP_NAME.lower()
    )


def test_config_dir_xdg_config_home(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/test")
    reload(gridsync)
    assert gridsync.config_dir == os.path.join(
        "/test", gridsync.APP_NAME.lower()
    )


def test_resource():
    assert gridsync.resource("test") == os.path.join(
        gridsync.pkgdir, "resources", "test"
    )


def test_load_settings_from_cheatcode(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), "pkgdir")
    providers_path = os.path.join(pkgdir, "resources", "providers")
    os.makedirs(providers_path)
    with open(os.path.join(providers_path, "test-test.json"), "w") as f:
        f.write('{"introducer": "pb://"}')
    monkeypatch.setattr("gridsync.pkgdir", pkgdir)
    settings = load_settings_from_cheatcode("test-test")
    assert settings["introducer"] == "pb://"


def test_load_settings_from_cheatcode_none(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), "pkgdir-empty")
    monkeypatch.setattr("gridsync.pkgdir", pkgdir)
    assert load_settings_from_cheatcode("test-test") is None
