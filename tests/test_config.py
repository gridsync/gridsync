# -*- coding: utf-8 -*-

import os

from gridsync.config import YamlConfig


def test_yaml_config_file():
    yaml_config = YamlConfig('test')
    assert yaml_config.filename == 'test'


def test_save(tmpdir):
    yaml_config = YamlConfig(os.path.join(str(tmpdir), 'test.yml'))
    yaml_config.save({'test': 'test'})
    with open(yaml_config.filename) as f:
        assert f.read() == 'test: test\n'


def test_load(tmpdir):
    yaml_config = YamlConfig(os.path.join(str(tmpdir), 'test.yml'))
    with open(yaml_config.filename, 'w') as f:
        f.write('test: test\n')
    assert yaml_config.load() == {'test': 'test'}
