# -*- coding: utf-8 -*-

import os

from gridsync.config import Config


def test_config_file():
    config = Config('test')
    assert config.config_file == 'test'


def test_save(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test.yml'))
    config.save({'test': 'test'})
    with open(config.config_file) as f:
        assert f.read() == 'test: test\n'


def test_load(tmpdir):
    config = Config(os.path.join(str(tmpdir), 'test.yml'))
    with open(config.config_file, 'w') as f:
        f.write('test: test\n')
    assert config.load() == {'test': 'test'}
