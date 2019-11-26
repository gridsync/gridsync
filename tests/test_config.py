# -*- coding: utf-8 -*-

import os

from gridsync.config import Config


def test_config_set(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_set.ini"))
    config.set("test_section", "test_option", "test_value")
    with open(config.filename) as f:
        assert f.read() == "[test_section]\ntest_option = test_value\n\n"


def test_config_get(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_get.ini"))
    with open(config.filename, "w") as f:
        f.write("[test_section]\ntest_option = test_value\n\n")
    assert config.get("test_section", "test_option") == "test_value"


def test_config_get_no_section_error(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_get_no_section_error.ini"))
    with open(config.filename, "w") as f:
        f.write("[test_section]\ntest_option = test_value\n\n")
    assert config.get("missing_section", "test_option") is None


def test_config_get_no_option_error(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_get_no_option_error.ini"))
    with open(config.filename, "w") as f:
        f.write("[test_section]\ntest_option = test_value\n\n")
    assert config.get("test_section", "missing_option") is None


def test_config_save(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_save.ini"))
    config.save({"test_section": {"test_option": "test_value"}})
    with open(config.filename) as f:
        assert f.read() == "[test_section]\ntest_option = test_value\n\n"


def test_config_load(tmpdir):
    config = Config(os.path.join(str(tmpdir), "test_load.ini"))
    with open(config.filename, "w") as f:
        f.write("[test_section]\ntest_option = test_value\n\n")
    assert config.load() == {"test_section": {"test_option": "test_value"}}
