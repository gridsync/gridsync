# -*- coding: utf-8 -*-

import os
import sys

from gridsync.config import Config


def test_config_dir():
    config = Config()
    if sys.platform == 'win32':
        expected_result = os.path.join(os.getenv('APPDATA'), 'Gridsync')
        assert config.config_dir == expected_result
    elif sys.platform == 'darwin':
        expected_result = os.path.join(os.path.expanduser('~'), 'Library',
                'Application Support', 'Gridsync')
        assert config.config_dir == expected_result
    else:
        expected_result = os.path.join(os.path.expanduser('~'), '.config',
                'gridsync')
        assert config.config_dir == expected_result

def test_default_config_file():
    config = Config()
    assert config.config_file == os.path.join(config.config_dir, 'config.yml')

def test_specified_config_file():
    config = Config(['test'])
    assert config.config_file == 'test'
