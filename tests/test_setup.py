# -*- coding: utf-8 -*-

import os
from unittest.mock import MagicMock

import pytest
import yaml

from gridsync.setup import (
    prompt_for_grid_name, validate_grid, prompt_for_folder_name,
    validate_folders, validate_settings, SetupRunner)
from gridsync.tahoe import Tahoe


def test_prompt_for_grid_name(monkeypatch):
    monkeypatch.setattr(
        'gridsync.setup.QInputDialog.getText',
        lambda a, b, c, d, e: ('NewGridName', 1)
    )
    assert prompt_for_grid_name('GridName') == ('NewGridName', 1)


def test_validate_grid_no_nickname(monkeypatch, tmpdir_factory):
    monkeypatch.setattr(
        'gridsync.setup.config_dir', str(tmpdir_factory.mktemp('config_dir')))
    monkeypatch.setattr(
        'gridsync.setup.prompt_for_grid_name', lambda x, y: ('NewGridName', 1))
    assert validate_grid({'nickname': None}) == {'nickname': 'NewGridName'}


def test_validate_grid_conflicting_introducer(monkeypatch, tmpdir_factory):
    config_dir = str(tmpdir_factory.mktemp('config_dir'))
    monkeypatch.setattr('gridsync.setup.config_dir', config_dir)
    nodedir = os.path.join(config_dir, 'ExistingGrid')
    os.makedirs(nodedir)
    with open(os.path.join(nodedir, 'tahoe.cfg'), 'w') as f:
        f.write('[client]\nintroducer.furl = pb://11111\n')
    monkeypatch.setattr(
        'gridsync.setup.prompt_for_grid_name', lambda x, y: ('NewGridName', 1))
    settings = {
        'nickname': 'ExistingGrid',
        'introducer': 'pb://22222'
    }
    assert validate_grid(settings) == {
        'nickname': 'NewGridName',
        'introducer': 'pb://22222'
    }


def test_validate_grid_conflicting_servers(monkeypatch, tmpdir_factory):
    config_dir = str(tmpdir_factory.mktemp('config_dir'))
    monkeypatch.setattr('gridsync.setup.config_dir', config_dir)
    private_dir = os.path.join(config_dir, 'ExistingGrid', 'private')
    os.makedirs(private_dir)
    servers = {
        'storage': {
            'v0-aaaaaaaa': {
                'ann': {
                    'anonymous-storage-FURL': 'pb://11111111',
                    'nickname': 'node-1'
                }
            }
        }
    }
    with open(os.path.join(private_dir, 'servers.yaml'), 'w') as f:
        f.write(yaml.safe_dump(servers, default_flow_style=False))
    monkeypatch.setattr(
        'gridsync.setup.prompt_for_grid_name', lambda x, y: ('NewGridName', 1))
    settings = {
        'nickname': 'ExistingGrid',
        'storage': {
            'anonymous-storage-FURL': 'pb://11111111',
            'nickname': 'node-1'
        }
    }
    assert validate_grid(settings) == {
        'nickname': 'NewGridName',
        'storage': {
            'anonymous-storage-FURL': 'pb://11111111',
            'nickname': 'node-1'
        }
    }


def test_prompt_for_folder_name(monkeypatch):
    monkeypatch.setattr(
        'gridsync.setup.QInputDialog.getText',
        lambda a, b, c, d, e: ('NewFolderName', 1)
    )
    assert prompt_for_folder_name('FolderName', 'Grid') == ('NewFolderName', 1)


def test_validate_folders_no_known_gateways():
    assert validate_folders({}, []) == {}


def test_validate_folders_skip_folder(monkeypatch, tmpdir_factory):
    gateway = Tahoe(
        os.path.join(str(tmpdir_factory.mktemp('config_dir')), 'SomeGrid'))
    gateway.magic_folders = {'FolderName': {}}
    monkeypatch.setattr(
        'gridsync.setup.prompt_for_folder_name',
        lambda x, y, z: (None, 0)
    )
    settings = {
        'nickname': 'SomeGrid',
        'magic-folders': {
            'FolderName': {
                'code': 'aaaaaaaa+bbbbbbbb'
            }
        }
    }
    assert validate_folders(settings, [gateway]) == {
        'nickname': 'SomeGrid',
        'magic-folders': {}
    }


def test_validate_folders_rename_folder(monkeypatch, tmpdir_factory):
    gateway = Tahoe(
        os.path.join(str(tmpdir_factory.mktemp('config_dir')), 'SomeGrid'))
    gateway.magic_folders = {'FolderName': {}}
    monkeypatch.setattr(
        'gridsync.setup.prompt_for_folder_name',
        lambda x, y, z: ('NewFolderName', 1)
    )
    settings = {
        'nickname': 'SomeGrid',
        'magic-folders': {
            'FolderName': {
                'code': 'aaaaaaaa+bbbbbbbb'
            }
        }
    }
    assert validate_folders(settings, [gateway]) == {
        'nickname': 'SomeGrid',
        'magic-folders': {
            'NewFolderName': {
                'code': 'aaaaaaaa+bbbbbbbb'
            }
        }
    }


def fake_validate(settings, *args):
    return settings


def test_validate_settings_strip_rootcap(monkeypatch):
    monkeypatch.setattr('gridsync.setup.validate_grid', fake_validate)
    settings = {'nickname': 'SomeGrid', 'rootcap': 'URI:ROOTCAP'}
    assert validate_settings(settings, [], None) == {'nickname': 'SomeGrid'}


def test_validate_settings_validate_folders(monkeypatch):
    monkeypatch.setattr('gridsync.setup.validate_grid', fake_validate)
    monkeypatch.setattr('gridsync.setup.validate_folders', fake_validate)
    settings = {
        'nickname': 'SomeGrid',
        'magic-folders': {
            'NewFolderName': {
                'code': 'aaaaaaaa+bbbbbbbb'
            }
        }
    }
    assert validate_settings(settings, [], None) == settings


def test_get_gateway_no_gateways():
    sr = SetupRunner([])
    assert not sr.get_gateway('pb://test', {})


@pytest.fixture(scope='module')
def fake_gateway():
    gateway = MagicMock()
    gateway.config_get.return_value = 'pb://introducer'
    gateway.get_storage_servers.return_value = {'Test': {}}
    return gateway


def test_get_gateway_match_from_introducer(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert sr.get_gateway('pb://introducer', {}) == fake_gateway


def test_get_gateway_match_from_servers(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert sr.get_gateway(None, {'Test': {}}) == fake_gateway


def test_get_gateway_no_match(fake_gateway):
    sr = SetupRunner([fake_gateway])
    assert not sr.get_gateway('pb://test', {})


def test_calculate_total_steps_1_already_joined_grid(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {'introducer': 'pb://introducer'}
    assert sr.calculate_total_steps(settings) == 1


def test_calculate_total_steps_5_need_to_join_grid(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {'introducer': 'pb://introducer.other'}
    assert sr.calculate_total_steps(settings) == 5


def test_calculate_total_steps_6_need_to_join_grid_and_1_folder(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {
        'introducer': 'pb://introducer.other',
        'magic-folders': {
            'FolderOne': {
                'code': 'URI+URI'
            }
        }
    }
    assert sr.calculate_total_steps(settings) == 6


def test_calculate_total_steps_7_need_to_join_grid_and_2_folders(fake_gateway):
    sr = SetupRunner([fake_gateway])
    settings = {
        'introducer': 'pb://introducer.other',
        'magic-folders': {
            'FolderOne': {
                'code': 'URI+URI'
            },
            'FolderTwo': {
                'code': 'URI+URI'
            }
        }
    }
    assert sr.calculate_total_steps(settings) == 7


def test_decode_icon_b64decode(tmpdir):
    sr = SetupRunner([])
    data = b'dGVzdDEyMzQ1'  # b64encode(b'test12345')
    dest = str(tmpdir.join('icon.png'))
    sr.decode_icon(data, dest)
    with open(dest) as f:
        assert f.read() == 'test12345'


def test_decode_icon_emit_got_icon_signal(qtbot, tmpdir):
    sr = SetupRunner([])
    data = b'dGVzdDEyMzQ1'  # b64encode(b'test12345')
    dest = str(tmpdir.join('icon.png'))
    with qtbot.wait_signal(sr.got_icon) as blocker:
        sr.decode_icon(data, dest)
    assert blocker.args == [dest]


def test_decode_icon_no_emit_got_icon_signal(qtbot, tmpdir):
    sr = SetupRunner([])
    data = b'0'  # raises binascii.Error
    dest = str(tmpdir.join('icon.png'))
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


@pytest.inlineCallbacks
def test_fetch_icon(monkeypatch, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join('icon.png'))
    monkeypatch.setattr('treq.get', fake_get)
    monkeypatch.setattr('treq.content', lambda _: b'0')
    yield sr.fetch_icon('http://example.org/icon.png', dest)
    with open(dest) as f:
        assert f.read() == '0'


@pytest.inlineCallbacks
def test_fetch_icon_emit_got_icon_signal(monkeypatch, qtbot, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join('icon.png'))
    monkeypatch.setattr('treq.get', fake_get)
    monkeypatch.setattr('treq.content', lambda _: b'0')
    with qtbot.wait_signal(sr.got_icon) as blocker:
        yield sr.fetch_icon('http://example.org/icon.png', dest)
    assert blocker.args == [dest]



@pytest.inlineCallbacks
def test_fetch_icon_no_emit_got_icon_signal(monkeypatch, qtbot, tmpdir):
    sr = SetupRunner([])
    dest = str(tmpdir.join('icon.png'))
    monkeypatch.setattr('treq.get', fake_get_code_500)
    with qtbot.assert_not_emitted(sr.got_icon):
        yield sr.fetch_icon('http://example.org/icon.png', dest)


def test_add_storage_servers(tmpdir):
    sr = SetupRunner([])
    nodedir = str(tmpdir.mkdir('TestGrid'))
    os.makedirs(os.path.join(nodedir, 'private'))
    sr.gateway = Tahoe(nodedir)
    storage_servers = {
        'node-1': {
            'anonymous-storage-FURL': 'pb://test',
            'nickname': 'One'
        }
    }
    sr.add_storage_servers(storage_servers)
    assert sr.gateway.get_storage_servers() == storage_servers


def test_add_storage_servers_no_add_missing_furl(tmpdir):
    sr = SetupRunner([])
    nodedir = str(tmpdir.mkdir('TestGrid'))
    os.makedirs(os.path.join(nodedir, 'private'))
    sr.gateway = Tahoe(nodedir)
    storage_servers = {
        'node-1': {
            'nickname': 'One'
        }
    }
    sr.add_storage_servers(storage_servers)
    assert sr.gateway.get_storage_servers() == {}
