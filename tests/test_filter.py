# -*- coding: utf-8 -*-

from collections import OrderedDict
import os
from unittest.mock import Mock

import pytest

from gridsync import pkgdir, config_dir, autostart_file_path
from gridsync.filter import get_filters, apply_filters


@pytest.fixture
def core():
    c = Mock()
    c.executable = '/tmp/test/tahoe.exe'
    gateway = Mock()
    gateway.name = 'TestGrid'
    storage_settings = OrderedDict()  # Because python3.5
    storage_settings['v0-22222'] = {
        'anonymous-storage-FURL': 'pb://333@444.example:1234/5555'
    }
    storage_settings['v0-66666'] = {
        'anonymous-storage-FURL': 'pb://777@888.example:1234/9999'
    }
    gateway.get_settings = Mock(return_value={
        'rootcap': 'URI:000:111',
        'introducer': 'pb://aaa@bbb.example:12345/ccc',
        'storage': storage_settings
    })
    gateway.magic_folders = OrderedDict()  # Because python3.5
    gateway.magic_folders['TestFolder'] = {
        'collective_dircap': 'URI:aaa:bbb',
        'upload_dircap': 'URI:ccc:ddd',
        'admin_dircap': 'URI:eee:fff',
        'directory': '/tmp/test/TestFolder',
        'member': 'Alice',
    }
    gateway.magic_folders['CatPics'] = {
        'collective_dircap': 'URI:ggg:hhh',
        'upload_dircap': 'URI:iii:jjj',
        'admin_dircap': 'URI:kkk:lll',
        'directory': '/tmp/test/CatPics',
        'member': 'Bob',
    }
    c.gui.main_window.gateways = [gateway]
    return c


@pytest.mark.parametrize(
    "pair",
    [
        (pkgdir, 'PkgDir'),
        (config_dir, 'ConfigDir'),
        (autostart_file_path, 'AutostartFilePath'),
        (os.path.expanduser('~'), 'HomeDir'),
    ]
)
def test_get_filters_pair_in_default_filters(core, pair):
    filters = get_filters(core)
    assert pair in filters


@pytest.mark.parametrize(
    'string',
    [
        pkgdir,
        config_dir,
        autostart_file_path,
        'TestGrid',
        'URI:000:111',
        'v0-22222',
        'pb://333@444.example:1234/5555',
        'v0-66666',
        'pb://777@888.example:1234/9999',
        'TestFolder',
        'URI:aaa:bbb',
        'URI:ccc:ddd',
        'URI:eee:fff',
        '/tmp/test/TestFolder',
        'Alice',
        'CatPics',
        'URI:ggg:hhh',
        'URI:iii:jjj',
        'URI:kkk:lll',
        '/tmp/test/CatPics',
        'Bob',
        os.path.expanduser('~'),
        '/tmp/test/tahoe.exe',
    ]
)
def test_apply_filters_string_not_in_result(core, string):
    filters = get_filters(core)
    in_str = 'Bob gave {} to Alice'.format(string)
    result = apply_filters(in_str, filters)
    assert string not in result


@pytest.mark.parametrize(
    'string,filtered',
    [
        (pkgdir, 'PkgDir'),
        (config_dir, 'ConfigDir'),
        (autostart_file_path, 'AutostartFilePath'),
        ('TestGrid', 'GatewayName:1'),
        ('URI:000:111', 'Rootcap:1'),
        ('v0-22222', 'StorageServerName:1:1'),
        ('pb://333@444.example:1234/5555', 'StorageServerFurl:1:1'),
        ('v0-66666', 'StorageServerName:1:2'),
        ('pb://777@888.example:1234/9999', 'StorageServerFurl:1:2'),
        ('URI:aaa:bbb', 'Folder:1:1:CollectiveDircap'),
        ('URI:ccc:ddd', 'Folder:1:1:UploadDircap'),
        ('URI:eee:fff', 'Folder:1:1:AdminDircap'),
        ('/tmp/test/TestFolder', 'Folder:1:1:Directory'),
        ('TestFolder', 'Folder:1:1:Name'),
        ('Alice', 'Folder:1:1:Member'),
        ('URI:ggg:hhh', 'Folder:1:2:CollectiveDircap'),
        ('URI:iii:jjj', 'Folder:1:2:UploadDircap'),
        ('URI:kkk:lll', 'Folder:1:2:AdminDircap'),
        ('/tmp/test/CatPics', 'Folder:1:2:Directory'),
        ('CatPics', 'Folder:1:2:Name'),
        ('Bob', 'Folder:1:2:Member'),
        (os.path.expanduser('~'), 'HomeDir'),
        ('/tmp/test/tahoe.exe', 'TahoeExecutablePath'),
    ]
)
def test_apply_filters_filtered_string_in_result(core, string, filtered):
    filters = get_filters(core)
    in_str = 'Bob gave {} to Alice'.format(string)
    result = apply_filters(in_str, filters)
    assert '<Filtered:{}>'.format(filtered) in result
