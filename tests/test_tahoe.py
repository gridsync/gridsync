# -*- coding: utf-8 -*-

import os

import pytest
from twisted.internet.defer import returnValue

from gridsync.errors import NodedirExistsError
from gridsync.tahoe import (
    is_valid_furl, get_nodedirs, TahoeError, TahoeCommandError, Tahoe)


@pytest.fixture(scope='module')
def tahoe(tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('tahoe')))
    with open(os.path.join(client.nodedir, 'tahoe.cfg'), 'w') as f:
        f.write('[node]\nnickname = default')
    with open(os.path.join(client.nodedir, 'icon.url'), 'w') as f:
        f.write('test_url')
    private_dir = os.path.join(os.path.join(client.nodedir, 'private'))
    os.mkdir(private_dir)
    with open(os.path.join(private_dir, 'aliases'), 'w') as f:
        f.write('test_alias: test_cap')
    with open(os.path.join(private_dir, 'rootcap'), 'w') as f:
        f.write('test_rootcap')
    with open(os.path.join(private_dir, 'magic_folders.yaml'), 'w') as f:
        f.write("test_folder: {directory: test_dir}")
    magic_folder_subdir = os.path.join(
        os.path.join(client.nodedir, 'magic-folders', 'Test'))
    os.makedirs(magic_folder_subdir)
    with open(os.path.join(magic_folder_subdir, 'tahoe.cfg'), 'w') as f:
        f.write('[magic_folder]\nlocal.directory = /Test')
    return client


def test_is_valid_furl():
    assert is_valid_furl('pb://abc234@example.org:12345/introducer')


def test_is_valid_furl_no_port():
    assert not is_valid_furl('pb://abc234@example.org/introducer')


def test_is_valid_furl_no_host_separator():
    assert not is_valid_furl('pb://abc234example.org:12345/introducer')


def test_is_valid_furl_invalid_char_in_connection_hint():
    assert not is_valid_furl('pb://abc234@exam/ple.org:12345/introducer')


def test_is_valid_furl_tub_id_not_base32():
    assert not is_valid_furl('pb://abc123@example.org:12345/introducer')


def test_get_nodedirs(tahoe, tmpdir_factory):
    basedir = str(tmpdir_factory.getbasetemp())
    assert tahoe.nodedir in get_nodedirs(basedir)


def test_get_nodedirs_empty(tahoe, tmpdir_factory):
    basedir = os.path.join(str(tmpdir_factory.getbasetemp()), 'non-existent')
    assert get_nodedirs(basedir) == []


def test_raise_tahoe_error():
    with pytest.raises(TahoeError):
        raise TahoeError


def test_raise_tahoe_command_error():
    with pytest.raises(TahoeCommandError):
        raise TahoeCommandError


def test_tahoe_default_nodedir():
    tahoe_client = Tahoe()
    assert tahoe_client.nodedir == os.path.join(
        os.path.expanduser('~'), '.tahoe')


def test_config_get(tahoe):
    assert tahoe.config_get('node', 'nickname') == 'default'


def test_config_set(tahoe):
    tahoe.config_set('node', 'nickname', 'test')
    assert tahoe.config_get('node', 'nickname') == 'test'


def test_get_settings(tahoe):
    settings = tahoe.get_settings()
    nickname = settings['nickname']
    icon_url = settings['icon_url']
    rootcap = settings['rootcap']
    assert (nickname, icon_url, rootcap) == (tahoe.name, 'test_url',
                                             'test_rootcap')

def test_export(tahoe, tmpdir_factory):
    dest = os.path.join(str(tmpdir_factory.getbasetemp()), 'settings.json')
    tahoe.export(dest)
    assert os.path.isfile(dest)


def test_get_aliases(tahoe):
    aliases = tahoe.get_aliases()
    assert aliases['test_alias:'] == 'test_cap'


def test_get_alias(tahoe):
    assert tahoe.get_alias('test_alias:') == 'test_cap'


def test_get_alias_append_colon(tahoe):
    assert tahoe.get_alias('test_alias') == 'test_cap'


def test_get_alias_not_found(tahoe):
    assert not tahoe.get_alias('missing_alias')


def test_load_magic_folders(tahoe):
    tahoe.load_magic_folders()
    assert tahoe.magic_folders['test_folder']['directory'] == 'test_dir'


def test_load_magic_folders_from_subdir(tahoe):
    tahoe.load_magic_folders()
    assert tahoe.magic_folders['Test']['directory'] == '/Test'


@pytest.inlineCallbacks
def test_tahoe_command_win32_monkeypatch(tahoe, monkeypatch):
    monkeypatch.setattr('sys.platform', 'win32')
    monkeypatch.setattr('sys.frozen', True, raising=False)
    monkeypatch.setattr('gridsync.tahoe.Tahoe._win32_popen',
                        lambda a, b, c, d: 'test output')
    output = yield tahoe.command(['test_command'])
    assert output == 'test output'


@pytest.inlineCallbacks
def test_tahoe_version(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', lambda x, y: 'test 1')
    version = yield tahoe.version()
    assert version == (None, '1')


@pytest.inlineCallbacks
def test_tahoe_create_client_nodedir_exists_error(tahoe):
    with pytest.raises(NodedirExistsError):
        output = yield tahoe.create_client()


@pytest.inlineCallbacks
def test_tahoe_create_client_args(tahoe, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda x: False)
    def return_args(_, args):
        returnValue(args)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', return_args)
    args = yield tahoe.create_client(nickname='test_nickname')
    assert set(['--nickname', 'test_nickname']).issubset(set(args))


@pytest.inlineCallbacks
def test_tahoe_create_client_args_compat(tahoe, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda x: False)
    def return_args(_, args):
        returnValue(args)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', return_args)
    args = yield tahoe.create_client(happy=7)
    assert set(['--shares-happy', '7']).issubset(set(args))


def test_parse_welcome_page(tahoe):  # tahoe-lafs=<1.12.1
    html = '''
        Connected to <span>3</span>of <span>10</span> known storage servers
        <td class="service-available-space">N/A</td>
        <td class="service-available-space">1kB</td>
        <td class="service-available-space">1kB</td>
    '''
    connected, known, space = tahoe._parse_welcome_page(html)
    assert (connected, known, space) == (3, 10, 2048)
