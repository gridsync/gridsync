# -*- coding: utf-8 -*-

import os
try:
    from unittest.mock import Mock, MagicMock
except ImportError:
    from mock import Mock, MagicMock

import pytest
from pytest_twisted import inlineCallbacks
import yaml

from twisted.test.proto_helpers import MemoryReactorClock

from gridsync.errors import TahoeError, TahoeCommandError, TahoeWebError
from gridsync.tahoe import is_valid_furl, get_nodedirs, Tahoe


def fake_get(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_get_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


def fake_put(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_put_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


def fake_post(*args, **kwargs):
    response = MagicMock()
    response.code = 200
    return response


def fake_post_code_500(*args, **kwargs):
    response = MagicMock()
    response.code = 500
    return response


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


def test_raise_tahoe_web_error():
    with pytest.raises(TahoeWebError):
        raise TahoeWebError


def test_tahoe_default_nodedir():
    tahoe_client = Tahoe()
    assert tahoe_client.nodedir == os.path.join(
        os.path.expanduser('~'), '.tahoe')


@pytest.mark.parametrize(
    'given,expected',
    [
        (123456, 123456),
        (0, 0),
        (None, 2000000),  # Default specified in gridsync.streamedlogs
    ]
)
def test_tahoe_set_streamedlogs_maxlen_from_config_txt(
        monkeypatch, given, expected):
    monkeypatch.setattr(
        'gridsync.tahoe.global_settings', {'debug': {'log_maxlen': given}})
    client = Tahoe()
    assert client.streamedlogs._buffer.maxlen == expected


def test_tahoe_load_newscap_from_global_settings(tahoe, monkeypatch):
    global_settings = {
        'news:{}'.format(tahoe.name): {
            'newscap': 'URI:NewscapFromSettings',
        }
    }
    monkeypatch.setattr('gridsync.tahoe.global_settings', global_settings)
    tahoe.load_newscap()
    assert tahoe.newscap == 'URI:NewscapFromSettings'


def test_tahoe_load_newscap_from_newscap_file(tahoe):
    with open(os.path.join(tahoe.nodedir, 'private', 'newscap'), 'w') as f:
        f.write('URI:NewscapFromFile')
    tahoe.load_newscap()
    assert tahoe.newscap == 'URI:NewscapFromFile'


def test_config_get(tahoe):
    assert tahoe.config_get('node', 'nickname') == 'default'


def test_config_set(tahoe):
    tahoe.config_set('node', 'nickname', 'test')
    assert tahoe.config_get('node', 'nickname') == 'test'


def test_get_settings(tahoe):
    settings = tahoe.get_settings()
    nickname = settings['nickname']
    icon_url = settings['icon_url']
    assert (nickname, icon_url) == (tahoe.name, 'test_url')


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


def test_add_alias(tahoe):
    tahoe.add_alias('added_alias', 'added_cap')
    assert tahoe.get_alias('added_alias') == 'added_cap'


def test_remove_alias(tahoe):
    tahoe.remove_alias('added_alias')
    assert not tahoe.get_alias('added_alias')


def test_remove_alias_idempotent(tahoe):
    tahoe.remove_alias('added_alias')
    assert not tahoe.get_alias('added_alias')


def test_get_storage_servers_empty(tahoe):
    assert tahoe.get_storage_servers() == {}


def test_get_storage_servers_non_empty(tahoe):
    data = {
        'storage': {
            'v0-aaa': {
                'ann': {
                    'anonymous-storage-FURL': 'pb://a.a',
                    'nickname': 'alice'
                }
            }
        }
    }
    with open(tahoe.servers_yaml_path, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))
    assert tahoe.get_storage_servers() == {
        'v0-aaa': {'anonymous-storage-FURL': 'pb://a.a', 'nickname': 'alice'}
    }


def test_add_storage_server(tahoe):
    tahoe.add_storage_server('v0-bbb', 'pb://b.b', 'bob')
    assert tahoe.get_storage_servers().get('v0-bbb') == {
        'anonymous-storage-FURL': 'pb://b.b', 'nickname': 'bob'
    }


def test_add_storage_servers(tmpdir):
    nodedir = str(tmpdir.mkdir('TestGrid'))
    os.makedirs(os.path.join(nodedir, 'private'))
    client = Tahoe(nodedir)
    storage_servers = {
        'node-1': {
            'anonymous-storage-FURL': 'pb://test',
            'nickname': 'One'
        }
    }
    client.add_storage_servers(storage_servers)
    assert client.get_storage_servers() == storage_servers


def test_add_storage_servers_no_add_missing_furl(tmpdir):
    nodedir = str(tmpdir.mkdir('TestGrid'))
    os.makedirs(os.path.join(nodedir, 'private'))
    client = Tahoe(nodedir)
    storage_servers = {
        'node-1': {
            'nickname': 'One'
        }
    }
    client.add_storage_servers(storage_servers)
    assert client.get_storage_servers() == {}


def test_load_magic_folders(tahoe):
    tahoe.load_magic_folders()
    assert tahoe.magic_folders['test_folder']['directory'] == 'test_dir'


@inlineCallbacks
def test_tahoe_command_win32_monkeypatch(tahoe, monkeypatch):
    monkeypatch.setattr('sys.platform', 'win32')
    monkeypatch.setattr('sys.frozen', True, raising=False)
    monkeypatch.setattr('gridsync.tahoe.Tahoe._win32_popen',
                        lambda a, b, c, d: 'test output')
    output = yield tahoe.command(['test_command'])
    assert output == 'test output'


@inlineCallbacks
def test_tahoe_get_features_multi_magic_folder_support(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', lambda x, y: 'test')
    output = yield tahoe.get_features()
    assert output == ('tahoe_exe', True, True)


@inlineCallbacks
def test_tahoe_get_features_no_multi_magic_folder_support(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', MagicMock(
        side_effect=TahoeCommandError('Unknown command: list')))
    output = yield tahoe.get_features()
    assert output == ('tahoe_exe', True, False)


@inlineCallbacks
def test_tahoe_get_features_no_magic_folder_support(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', MagicMock(
        side_effect=TahoeCommandError('Unknown command: magic-folder')))
    output = yield tahoe.get_features()
    assert output == ('tahoe_exe', False, False)


@inlineCallbacks
def test_tahoe_create_client_nodedir_exists_error(tahoe):
    with pytest.raises(FileExistsError):
        yield tahoe.create_client()


@inlineCallbacks
def test_tahoe_create_client_args(tahoe, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', mocked_command)
    yield tahoe.create_client(nickname='test_nickname')
    args = mocked_command.call_args[0][0]
    assert set(['--nickname', 'test_nickname']).issubset(set(args))


@inlineCallbacks
def test_tahoe_create_client_args_compat(tahoe, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', mocked_command)
    yield tahoe.create_client(happy=7)
    args = mocked_command.call_args[0][0]
    assert set(['--shares-happy', '7']).issubset(set(args))


@inlineCallbacks
def test_tahoe_create_client_args_hide_ip(tahoe, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda x: False)
    mocked_command = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', mocked_command)
    settings = {'hide-ip': True}
    yield tahoe.create_client(**settings)
    args = mocked_command.call_args[0][0]
    assert '--hide-ip' in args


@inlineCallbacks
def test_tahoe_create_client_add_storage_servers(tmpdir, monkeypatch):
    nodedir = str(tmpdir.mkdir('TestGrid'))
    os.makedirs(os.path.join(nodedir, 'private'))
    monkeypatch.setattr(
        'os.path.exists', lambda _: False)  # suppress FileExistsError
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', lambda x, y: None)
    client = Tahoe(nodedir)
    storage_servers = {
        'node-1': {
            'anonymous-storage-FURL': 'pb://test',
            'nickname': 'One'
        }
    }
    settings = {'nickname': 'TestGrid', 'storage': storage_servers}
    yield client.create_client(**settings)
    assert client.get_storage_servers() == storage_servers


def write_pidfile(nodedir):
    pidfile = os.path.join(nodedir, 'twistd.pid')
    with open(pidfile, 'w') as f:
        f.write('4194305')
    return pidfile


def test_tahoe_stop_win32_monkeypatch(tahoe, monkeypatch):
    pidfile = write_pidfile(tahoe.nodedir)
    killed = [None]

    def fake_kill(pid, _):
        killed[0] = pid
    removed = [None]

    def fake_remove(file):
        removed[0] = file
    monkeypatch.setattr('os.kill', fake_kill)
    monkeypatch.setattr('os.remove', fake_remove)
    monkeypatch.setattr('gridsync.tahoe.get_nodedirs', lambda _: [])
    monkeypatch.setattr('sys.platform', 'win32')
    tahoe.stop()
    assert (killed[0], removed[0]) == (4194305, pidfile)


@inlineCallbacks
def test_tahoe_stop_linux_monkeypatch(tahoe, monkeypatch):
    mocked_command = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', mocked_command)
    monkeypatch.setattr('sys.platform', 'linux')
    write_pidfile(tahoe.nodedir)
    yield tahoe.stop()
    args = mocked_command.call_args[0][0]
    assert args == ['stop']


@pytest.mark.parametrize('locked,call_count', [(True, 1), (False, 0)])
@inlineCallbacks
def test_tahoe_stop_locked(locked, call_count, tahoe, monkeypatch):
    lock = MagicMock()
    lock.locked = locked
    lock.acquire = MagicMock()
    lock.release = MagicMock()
    tahoe.lock = lock
    monkeypatch.setattr('os.path.isfile', lambda x: True)
    monkeypatch.setattr('sys.platform', 'linux')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', MagicMock())
    monkeypatch.setattr('os.remove', MagicMock())
    yield tahoe.stop()
    assert (lock.acquire.call_count, lock.release.call_count) == (
        call_count, call_count)


@pytest.mark.parametrize(
    'tahoe_state,call_count',
    [
        (Tahoe.STOPPED, 1),  # restart completed
        (Tahoe.STARTING, 0),  # restart aborted
        (Tahoe.STARTED, 1),  # restart completed
        (Tahoe.STOPPING, 0),  # restart aborted
    ]
)
@inlineCallbacks
def test_tahoe_restart(tahoe_state, call_count, tahoe, monkeypatch):
    mocked_start = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.stop', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.Tahoe.start', mocked_start)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.deferLater', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.set_preference', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.get_preference', MagicMock())
    tahoe.state = tahoe_state
    yield tahoe.restart()
    assert mocked_start.call_count == call_count


@inlineCallbacks
def test_get_grid_status(tahoe, monkeypatch):
    json_content = b'''{
        "introducers": {
            "statuses": [
                "Connected to introducer.local:3456 via tcp"
            ]
        },
        "servers": [
            {
                "connection_status": "Trying to connect",
                "nodeid": "v0-aaaaaaaaaaaaaaaaaaaaaaaa",
                "last_received_data": null,
                "version": null,
                "available_space": null,
                "nickname": "node1"
            },
            {
                "connection_status": "Connected to tcp:node2:4567 via tcp",
                "nodeid": "v0-bbbbbbbbbbbbbbbbbbbbbbbb",
                "last_received_data": 1509126406.799392,
                "version": "tahoe-lafs/1.12.1",
                "available_space": 1024,
                "nickname": "node2"
            },
            {
                "connection_status": "Connected to tcp:node3:5678 via tcp",
                "nodeid": "v0-cccccccccccccccccccccccc",
                "last_received_data": 1509126406.799392,
                "version": "tahoe-lafs/1.12.1",
                "available_space": 2048,
                "nickname": "node3"
            }
        ]
    }'''
    monkeypatch.setattr('treq.get', fake_get)
    monkeypatch.setattr('treq.content', lambda _: json_content)
    num_connected, num_known, available_space = yield tahoe.get_grid_status()
    assert (num_connected, num_known, available_space) == (2, 3, 3072)


@inlineCallbacks
def test_get_connected_servers(tahoe, monkeypatch):
    html = b'Connected to <span>3</span>of <span>10</span>'
    monkeypatch.setattr('treq.get', fake_get)
    monkeypatch.setattr('treq.content', lambda _: html)
    output = yield tahoe.get_connected_servers()
    assert output == 3


@inlineCallbacks
def test_is_ready_false_not_shares_happy(tahoe, monkeypatch):
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_is_ready_false_not_connected_servers(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_connected_servers', lambda _: None)
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_is_ready_true(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_connected_servers', lambda _: 10)
    output = yield tahoe.is_ready()
    assert output is True


@inlineCallbacks
def test_is_ready_false_connected_less_than_happy(tahoe, monkeypatch):
    tahoe.shares_happy = 7
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_connected_servers', lambda _: 3)
    output = yield tahoe.is_ready()
    assert output is False


@inlineCallbacks
def test_await_ready(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.is_ready', lambda _: True)
    yield tahoe.await_ready()
    assert True


@inlineCallbacks
def test_tahoe_mkdir(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post)
    monkeypatch.setattr('treq.content', lambda _: b'URI:DIR2:abc234:def567')
    output = yield tahoe.mkdir()
    assert output == 'URI:DIR2:abc234:def567'


@inlineCallbacks
def test_tahoe_mkdir_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post_code_500)
    monkeypatch.setattr('treq.content', lambda _: b'test content')
    with pytest.raises(TahoeWebError):
        yield tahoe.mkdir()


@inlineCallbacks
def test_create_rootcap(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:abc')
    output = yield tahoe.create_rootcap()
    assert output == 'URI:DIR2:abc'


@inlineCallbacks
def test_create_rootcap_already_exists(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:abc')
    yield tahoe.create_rootcap()
    with pytest.raises(OSError):
        yield tahoe.create_rootcap()


@inlineCallbacks
def test_tahoe_upload(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:abc')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.put', fake_put)
    monkeypatch.setattr('treq.content', lambda _: b'test_cap')
    yield tahoe.create_rootcap()
    output = yield tahoe.upload(tahoe.rootcap_path)
    assert output == 'test_cap'


@inlineCallbacks
def test_tahoe_upload_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:abc')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.put', fake_put_code_500)
    monkeypatch.setattr('treq.content', lambda _: b'test content')
    yield tahoe.create_rootcap()
    with pytest.raises(TahoeWebError):
        yield tahoe.upload(tahoe.rootcap_path)


@inlineCallbacks
def test_tahoe_download(tahoe, monkeypatch):
    def fake_collect(response, collector):
        collector(b'test_content')  # f.write(b'test_content')

    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.get', fake_get)
    monkeypatch.setattr('treq.collect', fake_collect)
    location = os.path.join(tahoe.nodedir, 'test_downloaded_file')
    yield tahoe.download('test_cap', location)
    with open(location, 'r') as f:
        content = f.read()
        assert content == 'test_content'


@inlineCallbacks
def test_tahoe_download_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.get', fake_get_code_500)
    monkeypatch.setattr('treq.content', lambda _: b'test content')
    with pytest.raises(TahoeWebError):
        yield tahoe.download('test_cap', os.path.join(tahoe.nodedir, 'nofile'))


@inlineCallbacks
def test_tahoe_link(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post)
    yield tahoe.link('test_dircap', 'test_childname', 'test_childcap')
    assert True


@inlineCallbacks
def test_tahoe_link_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post_code_500)
    monkeypatch.setattr('treq.content', lambda _: b'test content')
    with pytest.raises(TahoeWebError):
        yield tahoe.link('test_dircap', 'test_childname', 'test_childcap')


@inlineCallbacks
def test_tahoe_unlink(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post)
    yield tahoe.unlink('test_dircap', 'test_childname')
    assert True


@inlineCallbacks
def test_tahoe_unlink_fail_code_500(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('treq.post', fake_post_code_500)
    monkeypatch.setattr('treq.content', lambda _: b'test content')
    with pytest.raises(TahoeWebError):
        yield tahoe.unlink('test_dircap', 'test_childname')


def test_local_magic_folder_exists_true(tahoe):
    tahoe.magic_folders['LocalTestFolder'] = {}
    assert tahoe.local_magic_folder_exists('LocalTestFolder')


def test_local_magic_folder_exists_false(tahoe):
    assert not tahoe.local_magic_folder_exists('LocalTestFolder')


def test_remote_magic_folder_exists_true(tahoe):
    tahoe.remote_magic_folders['RemoteTestFolder'] = {}
    assert tahoe.remote_magic_folder_exists('RemoteTestFolder')


def test_remote_magic_folder_exists_false(tahoe):
    assert not tahoe.local_magic_folder_exists('RemoteTestFolder')


def test_magic_folder_exists_true(tahoe):
    tahoe.magic_folders['ExistingTestFolder'] = {}
    assert tahoe.magic_folder_exists('ExistingTestFolder')


def test_magic_folder_exists_false(tahoe):
    assert not tahoe.magic_folder_exists('ExistingTestFolder')


@inlineCallbacks
def test_tahoe_magic_folder_invite(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.is_ready', lambda _: True)
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_admin_dircap', lambda x, y: 'URI:a')
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_collective_dircap', lambda x, y: 'URI:c')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda x, y, z: 'URI:u')
    output = yield tahoe.magic_folder_invite('Test Folder', 'Bob')
    assert output == 'URI:c+URI:u'


@inlineCallbacks
def test_tahoe_magic_folder_invite_raise_tahoe_error(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.is_ready', lambda _: True)
    with pytest.raises(TahoeError):
        yield tahoe.magic_folder_invite('Test Folder', 'Bob')


@inlineCallbacks
def test_tahoe_magic_folder_uninvite(tahoe, monkeypatch):
    monkeypatch.setattr('gridsync.tahoe.Tahoe.unlink', lambda x, y, z: None)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.get_alias', lambda x, y: 'test')
    yield tahoe.magic_folder_uninvite('Test Folder', 'Bob')
    assert True


@inlineCallbacks
def test_tahoe_magic_folder_uninvite_from_subclient(tahoe, monkeypatch):
    tahoe.magic_folders['TestUninviteFolder'] = {'client': MagicMock()}
    monkeypatch.setattr('gridsync.tahoe.Tahoe.unlink', lambda x, y, z: None)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.get_alias', lambda x, y: 'test')
    yield tahoe.magic_folder_uninvite('TestUninviteFolder', 'Bob')
    assert True


@inlineCallbacks
def test_upgrade_legacy_config(tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('tahoe-legacy')))
    os.makedirs(os.path.join(client.nodedir, 'private'))
    subclient_nodedir = os.path.join(client.magic_folders_dir, 'LegacyFolder')
    privatedir = os.path.join(subclient_nodedir, 'private')
    os.makedirs(privatedir)
    with open(os.path.join(privatedir, 'collective_dircap'), 'w') as f:
        f.write('URI:COLLECTIVE_DIRCAP')
    with open(os.path.join(privatedir, 'magic_folder_dircap'), 'w') as f:
        f.write('URI:MAGIC_FOLDER_DIRCAP')
    db_path = os.path.join(privatedir, 'magicfolderdb.sqlite')
    with open(db_path, 'a'):
        os.utime(db_path, None)
    subclient = Tahoe(subclient_nodedir)
    subclient.config_set('magic_folder', 'local.directory', '/LegacyFolder')
    subclient.config_set('magic_folder', 'poll_interval', '10')

    yield client.upgrade_legacy_config()

    yaml_path = os.path.join(client.nodedir, 'private', 'magic_folders.yaml')
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    folder_data = data['magic-folders']['LegacyFolder']
    assert folder_data['collective_dircap'] == 'URI:COLLECTIVE_DIRCAP'
    assert folder_data['upload_dircap'] == 'URI:MAGIC_FOLDER_DIRCAP'
    assert folder_data['directory'] == '/LegacyFolder'
    assert folder_data['poll_interval'] == '10'
    assert os.path.exists(os.path.join(
        client.nodedir, 'private', 'magicfolder_LegacyFolder.sqlite'))
    assert os.path.exists(client.magic_folders_dir + '.backup')
    assert not os.path.exists(client.magic_folders_dir)


def test_tahoe_get_log_sort_output(tahoe):
    tahoe.streamedlogs._buffer.append(b'{"C": 3, "A": 1, "B": 2}')
    output = tahoe.get_log()
    assert output == '{"A": 1, "B": 2, "C": 3}'


def test_tahoe_get_log_apply_filter(tahoe):
    tahoe.streamedlogs._buffer.append(
        b'{"action_type": "magic-folder:full-scan", "nickname": "TestGrid"}')
    output = tahoe.get_log(apply_filter=True)
    assert output == (
        '{"action_type": "magic-folder:full-scan", '
        '"nickname": "<Filtered:GatewayName:95e65be>"}'
    )


def test_tahoe_get_log_apply_filter_use_identifier(tahoe):
    tahoe.streamedlogs._buffer.append(
        b'{"action_type": "magic-folder:full-scan", "nickname": "TestGrid"}')
    output = tahoe.get_log(apply_filter=True, identifier='1')
    assert output == (
        '{"action_type": "magic-folder:full-scan", '
        '"nickname": "<Filtered:GatewayName:1>"}'
    )


@inlineCallbacks
def test_tahoe_start_use_tor_false(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('tahoe-start')))
    privatedir = os.path.join(client.nodedir, 'private')
    os.makedirs(privatedir)
    nodeurl = 'http://127.0.0.1:54321'
    client.set_nodeurl(nodeurl)
    with open(os.path.join(client.nodedir, 'node.url'), 'w') as f:
        f.write(nodeurl)
    with open(os.path.join(privatedir, 'api_auth_token'), 'w') as f:
        f.write('1234567890')
    client.config_set('client', 'shares.happy', '99999')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', lambda x, y, z: 9999)
    yield client.start()
    assert not client.use_tor


@inlineCallbacks
def test_tahoe_starts_streamedlogs(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.command',
        lambda self, args, callback_trigger=None: 9999,
    )
    reactor = MemoryReactorClock()
    tahoe = tahoe_factory(reactor)
    tahoe.monitor = Mock()
    tahoe.config_set('client', 'shares.needed', '3')
    tahoe.config_set('client', 'shares.happy', '7')
    tahoe.config_set('client', 'shares.total', '10')
    yield tahoe.start()
    assert tahoe.streamedlogs.running
    (host, port, _, _, _) = reactor.tcpClients.pop(0)
    assert (host, port) == ("example.invalid", 12345)


@inlineCallbacks
def test_tahoe_stops_streamedlogs(monkeypatch, tahoe_factory):
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.command',
        lambda self, args, callback_trigger=None: 9999,
    )
    tahoe = tahoe_factory(MemoryReactorClock())
    tahoe.monitor = Mock()
    tahoe.config_set('client', 'shares.needed', '3')
    tahoe.config_set('client', 'shares.happy', '7')
    tahoe.config_set('client', 'shares.total', '10')
    yield tahoe.start()
    write_pidfile(tahoe.nodedir)
    yield tahoe.stop()
    assert not tahoe.streamedlogs.running


@inlineCallbacks
def test_tahoe_start_use_tor_true(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('tahoe-start')))
    privatedir = os.path.join(client.nodedir, 'private')
    os.makedirs(privatedir)
    nodeurl = 'http://127.0.0.1:54321'
    client.set_nodeurl(nodeurl)
    with open(os.path.join(client.nodedir, 'node.url'), 'w') as f:
        f.write(nodeurl)
    with open(os.path.join(privatedir, 'api_auth_token'), 'w') as f:
        f.write('1234567890')
    client.config_set('client', 'shares.happy', '99999')
    client.config_set('connections', 'tcp', 'tor')
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', lambda x, y, z: 9999)
    yield client.start()
    assert client.use_tor


@inlineCallbacks
def test__create_magic_folder_write_yaml(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('nodedir')))
    privatedir = os.path.join(client.nodedir, 'private')
    os.makedirs(privatedir)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:aaa')
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_json',
        lambda x, y: ["dirnode", {"ro_uri": "URI:DIR2-RO:bbb"}]
    )
    monkeypatch.setattr('gridsync.tahoe.Tahoe.link', MagicMock())
    folder_path = str(tmpdir_factory.mktemp('TestFolder'))
    yield client._create_magic_folder(folder_path, 'testalias', 123)
    with open(os.path.join(privatedir, 'magic_folders.yaml')) as f:
        yaml_data = yaml.safe_load(f)
    assert yaml_data == {
        'magic-folders': {
            os.path.basename(folder_path): {
                'directory': folder_path,
                'collective_dircap': 'URI:DIR2-RO:bbb',
                'upload_dircap': 'URI:DIR2:aaa',
                'poll_interval': 123,
            }
        }
    }


@inlineCallbacks
def test__create_magic_folder_add_alias(monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('nodedir')))
    privatedir = os.path.join(client.nodedir, 'private')
    os.makedirs(privatedir)
    monkeypatch.setattr('gridsync.tahoe.Tahoe.mkdir', lambda _: 'URI:DIR2:aaa')
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.get_json',
        lambda x, y: ["dirnode", {"ro_uri": "URI:DIR2-RO:bbb"}]
    )
    monkeypatch.setattr('gridsync.tahoe.Tahoe.link', MagicMock())
    folder_path = str(tmpdir_factory.mktemp('TestFolder'))
    yield client._create_magic_folder(folder_path, 'testalias', 123)
    assert client.get_alias('testalias') == 'URI:DIR2:aaa'


@pytest.mark.parametrize(
    'exception_raised,num_calls',
    [
        (None, 1),
        (Exception, 2),
        (TahoeError, 2),
    ]
)
@inlineCallbacks
def test_create_magic_folder_call__create_magic_folder(
        exception_raised, num_calls, monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('nodedir')))
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.Tahoe.load_magic_folders', MagicMock())
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.link_magic_folder_to_rootcap', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.deferLater', MagicMock())
    m = MagicMock(side_effect=exception_raised)
    monkeypatch.setattr('gridsync.tahoe.Tahoe._create_magic_folder', m)
    folder_path = str(tmpdir_factory.mktemp('TestFolder'))
    if exception_raised:
        with pytest.raises(exception_raised):
            yield client.create_magic_folder(folder_path)
    else:
        yield client.create_magic_folder(folder_path)
    assert m.call_count == num_calls


@pytest.mark.parametrize(
    'admin_dircap,num_add_alias_calls',
    [
        (None, 0),
        ('URI:TEST', 1),
    ]
)
@inlineCallbacks
def test_create_magic_folder_call_command_magic_folder_join_and_create_alias(
        admin_dircap, num_add_alias_calls, monkeypatch, tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('nodedir')))
    monkeypatch.setattr('gridsync.tahoe.Tahoe.await_ready', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.Tahoe.load_magic_folders', MagicMock())
    monkeypatch.setattr(
        'gridsync.tahoe.Tahoe.link_magic_folder_to_rootcap', MagicMock())
    monkeypatch.setattr('gridsync.tahoe.Tahoe.command', MagicMock())
    m = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.add_alias', m)
    folder_path = str(tmpdir_factory.mktemp('TestFolder'))
    yield client.create_magic_folder(folder_path, 'CAP1:CAP2', admin_dircap)
    assert m.call_count == num_add_alias_calls


@pytest.mark.parametrize(
    'admin_dircap,collective_dircap,upload_dircap,exception_raised,call_count',
    [
        ('URI:admin', 'URI:collective', 'URI:upload', None, 1),
        ('URI:admin', None, 'URI:upload', TahoeError, 0),
        ('URI:admin', 'URI:collective', None, TahoeError, 0),
    ]
)
@inlineCallbacks
def test_restore_magic_folder_raise_tahoe_error(
        admin_dircap,
        collective_dircap,
        upload_dircap,
        exception_raised,
        call_count,
        monkeypatch,
        tmpdir_factory):
    client = Tahoe(str(tmpdir_factory.mktemp('nodedir')))
    client.remote_magic_folders['TestFolder'] = {
        'admin_dircap': admin_dircap,
        'collective_dircap': collective_dircap,
        'upload_dircap': upload_dircap,
    }
    m = MagicMock()
    monkeypatch.setattr('gridsync.tahoe.Tahoe.create_magic_folder', m)
    dest = str(tmpdir_factory.mktemp('TestFolderDestination'))
    if exception_raised:
        with pytest.raises(exception_raised):
            yield client.restore_magic_folder('TestFolder', dest)
    else:
        yield client.restore_magic_folder('TestFolder', dest)
    assert m.call_count == call_count
