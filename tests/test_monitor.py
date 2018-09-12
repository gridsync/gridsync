# -*- coding: utf-8 -*-

import pytest

from gridsync.monitor import MagicFolderChecker


@pytest.fixture(scope='function')
def mfc():
    return MagicFolderChecker(None, 'TestFolder')


def test_magic_folder_checker_name(mfc):
    assert mfc.name == 'TestFolder'


def test_magic_folder_checker_remote_default_false(mfc):
    assert mfc.remote is False


status_data = [
    {
        'kind': 'upload',
        'path': 'file_4',
        'percent_done': 0,
        'queued_at': 1,
        'size': 2560,
        'status': 'queued'
    },
    {
        'kind': 'upload',
        'path': 'file_3',
        'percent_done': 0,
        'queued_at': 1,
        'size': None,
        'status': 'queued'
    },
    {
        'kind': 'upload',
        'path': 'file_2',
        'percent_done': 50.0,
        'queued_at': 1,
        'size': 1024,
        'started_at': 1,
        'status': 'started'
    },
    {
        'kind': 'upload',
        'path': 'file_1',
        'percent_done': 100.0,
        'queued_at': 1,
        'size': 512,
        'started_at': 1,
        'status': 'success',
        'success_at': 1
    }
]


def test_emit_transfer_progress_updated(mfc, qtbot):
    with qtbot.wait_signal(mfc.transfer_progress_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [1024, 4096]  # bytes transferred, bytes total


def test_emit_transfer_speed_updated(mfc, monkeypatch, qtbot):
    mfc.sync_time_started = 1
    monkeypatch.setattr('time.time', lambda: 2)  # One second has passed
    with qtbot.wait_signal(mfc.transfer_speed_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [1024]  # bytes per second


def test_emit_transfer_seconds_remaining_updated(mfc, monkeypatch, qtbot):
    mfc.sync_time_started = 1
    monkeypatch.setattr('time.time', lambda: 2)  # One second has passed
    with qtbot.wait_signal(mfc.transfer_seconds_remaining_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [3]  # seconds remaining


def test_parse_status_set_sync_time_started_by_earliest_time(mfc):
    mfc.parse_status([
        {'kind': 'upload', 'path': 'two', 'status': 'queued', 'queued_at': 2},
        {'kind': 'upload', 'path': 'one', 'status': 'queued', 'queued_at': 1}
    ])
    assert mfc.sync_time_started == 1


def test_parse_status_return_values_syncing(mfc):
    state, kind, path, failures = mfc.parse_status(status_data)
    assert (state, kind, path, failures) == (1, 'upload', 'file_2', [])


def test_parse_status_state_up_to_date(mfc):
    state, _, _, _ = mfc.parse_status({})
    assert state == 2


def test_parse_status_append_failure(mfc):
    task = {'kind': 'upload', 'status': 'failure'}
    _, _, _, failures = mfc.parse_status([task])
    assert failures == [task]


def test_process_status_remote_scan_needed(mfc):
    mfc.state = 1
    assert mfc.process_status(status_data) is True


def test_process_status_emit_status_updated_syncing(mfc, monkeypatch, qtbot):
    with qtbot.wait_signal(mfc.status_updated) as blocker:
        mfc.process_status(status_data)
    assert blocker.args == [1]


def test_process_status_still_syncing_no_emit_status_updated(mfc, qtbot):
    mfc.state = 1
    with qtbot.assertNotEmitted(mfc.status_updated):
        mfc.process_status(status_data)


def test_process_status_emit_status_updated_scanning(mfc, monkeypatch, qtbot):
    mfc.state = 1
    monkeypatch.setattr(
        'gridsync.monitor.MagicFolderChecker.parse_status',
        lambda x, y: (2, 'upload', 'file_0', [])
    )
    with qtbot.wait_signal(mfc.status_updated) as blocker:
        mfc.process_status(status_data)
    assert blocker.args == [99]


def test_process_status_emit_status_updated_up_to_date(
        mfc, monkeypatch, qtbot):
    mfc.state = 99
    monkeypatch.setattr(
        'gridsync.monitor.MagicFolderChecker.parse_status',
        lambda x, y: (2, 'upload', 'file_0', [])
    )
    with qtbot.wait_signal(mfc.status_updated) as blocker:
        mfc.process_status(status_data)
    assert blocker.args == [2]


def test_process_status_emit_sync_finished(mfc, monkeypatch, qtbot):
    mfc.state = 99
    monkeypatch.setattr(
        'gridsync.monitor.MagicFolderChecker.parse_status',
        lambda x, y: (2, 'upload', 'file_0', [])
    )
    with qtbot.wait_signal(mfc.sync_finished):
        mfc.process_status(status_data)


def test_process_status_emit_sync_started(mfc, monkeypatch, qtbot):
    mfc.state = 99
    monkeypatch.setattr(
        'gridsync.monitor.MagicFolderChecker.parse_status',
        lambda x, y: (1, 'upload', 'file_0', [])
    )
    with qtbot.wait_signal(mfc.sync_started):
        mfc.process_status(status_data)


def test_compare_states_emit_file_updated(mfc, qtbot):
    previous = {}
    current = {
        1234567890.123456: {
            'size': 1024,
            'mtime': 1234567890.123456,
            'deleted': False,
            'cap': 'URI:CHK:aaaaaa:bbbbbb:1:1:1024',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    with qtbot.wait_signal(mfc.file_updated):
        mfc.compare_states(current, previous)


def test_compare_states_file_added(mfc):
    previous = {}
    current = {
        1234567890.123456: {
            'size': 1024,
            'mtime': 1234567890.123456,
            'deleted': False,
            'cap': 'URI:CHK:aaaaaa:bbbbbb:1:1:1024',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]['action'] == 'added'


def test_compare_states_file_updated(mfc):
    previous = {
        1234567890.123456: {
            'size': 1024,
            'mtime': 1234567890.123456,
            'deleted': False,
            'cap': 'URI:CHK:aaaaaa:bbbbbb:1:1:1024',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    current = {
        1234567891.123456: {
            'size': 2048,
            'mtime': 1234567891.123456,
            'deleted': False,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]['action'] == 'updated'


def test_compare_states_file_deleted(mfc):
    previous = {
        1234567891.123456: {
            'size': 2048,
            'mtime': 1234567891.123456,
            'deleted': False,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    current = {
        1234567892.123456: {
            'size': 2048,
            'mtime': 1234567892.123456,
            'deleted': True,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]['action'] == 'deleted'


def test_compare_states_file_restored(mfc):
    previous = {
        1234567892.123456: {
            'size': 2048,
            'mtime': 1234567892.123456,
            'deleted': True,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    current = {
        1234567893.123456: {
            'size': 2048,
            'mtime': 1234567893.123456,
            'deleted': False,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]['action'] == 'restored'


def test_compare_states_directory_created(mfc):
    previous = {
        1234567893.123456: {
            'size': 2048,
            'mtime': 1234567893.123456,
            'deleted': False,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        }
    }
    current = {
        1234567893.123456: {
            'size': 2048,
            'mtime': 1234567893.123456,
            'deleted': False,
            'cap': 'URI:CHK:cccccc:dddddd:1:1:2048',
            'path': 'file_1',
            'member': 'admin'
        },
        1234567894.123456: {
            'size': 0,
            'mtime': 1234567894.123456,
            'deleted': False,
            'cap': 'URI:DIR:eeeeee:ffffff',
            'path': 'subdir/',
            'member': 'admin'
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]['action'] == 'created'
