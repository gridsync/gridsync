# -*- coding: utf-8 -*-

import os

from gridsync.config import Config, YamlConfig


def test_config_set(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test_set.ini'))
    config.set('test_section', 'test_option', 'test_value')
    with open(config.filename) as f:
        assert f.read() == '[test_section]\ntest_option = test_value\n\n'


def test_config_get(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test_get.ini'))
    with open(config.filename, 'w') as f:
        f.write('[test_section]\ntest_option = test_value\n\n')
    assert config.get('test_section', 'test_option') == 'test_value'


def test_config_save(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test_save.ini'))
    config.save({'test_section': {'test_option': 'test_value'}})
    with open(config.filename) as f:
        assert f.read() == '[test_section]\ntest_option = test_value\n\n'


def test_config_load(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test_load.ini'))
    with open(config.filename, 'w') as f:
        f.write('[test_section]\ntest_option = test_value\n\n')
    config.load() == {'test_section': {'test_option': 'test_value'}}


def test_yaml_config_save(tmpdir):
    yaml_config = YamlConfig(os.path.join(str(tmpdir), 'test_save.yml'))
    yaml_config.save({'test': 'test'})
    with open(yaml_config.filename) as f:
        assert f.read() == 'test: test\n'


def test_yaml_config_load(tmpdir):
    yaml_config = YamlConfig(os.path.join(str(tmpdir), 'test_load.yml'))
    with open(yaml_config.filename, 'w') as f:
        f.write('test: test\n')
    assert yaml_config.load() == {'test': 'test'}
