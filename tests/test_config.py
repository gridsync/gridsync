# -*- coding: utf-8 -*-

import os
import sys

from gridsync.config import Config


def test_config_dir():
    config = Config()
    if sys.platform == 'win32':
        assert config.config_dir == os.path.join(os.getenv('APPDATA'),
                                                 'Gridsync')
    elif sys.platform == 'darwin':
        assert config.config_dir == os.path.join(
            os.path.expanduser('~'), 'Library', 'Application Support',
            'Gridsync')
    else:
        assert config.config_dir == os.path.join(os.path.expanduser('~'),
                                                 '.config', 'gridsync')


def test_config_dir_win32(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv('APPDATA', 'C:\\Users\\test\\AppData\\Roaming')
    assert Config().config_dir == os.path.join(os.getenv('APPDATA'),
                                               'Gridsync')


def test_config_dir_darwin(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assert Config().config_dir == os.path.join(
        os.path.expanduser('~'), 'Library', 'Application Support', 'Gridsync')


def test_config_dir_other(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    assert Config().config_dir == os.path.join(os.path.expanduser('~'),
                                               '.config', 'gridsync')


def test_config_dir_xdg_config_home(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv('XDG_CONFIG_HOME', '/test')
    assert Config().config_dir == os.path.join('/test', 'gridsync')


def test_config_file():
    config = Config(['test'])
    assert config.config_file == 'test'


def test_save(tmpdir):
    config = Config([os.path.join(str(tmpdir), 'test.yml')])
    config.save({'test': 'test'})
    with open(config.config_file) as f:
        assert f.read() == 'test: test\n'


def test_load(tmpdir):
    config = Config([os.path.join(str(tmpdir), 'test.yml')])
    with open(config.config_file, 'w') as f:
        f.write('test: test\n')
    assert config.load() == {'test': 'test'}
