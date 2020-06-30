# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, Mock, call

import pytest
from pytest_twisted import inlineCallbacks

from gridsync.monitor import MagicFolderChecker, GridChecker, Monitor


@pytest.fixture(scope="function")
def mfc():
    mock_gateway = Mock()
    mock_gateway.monitor.grid_checker.is_connected = True
    checker = MagicFolderChecker(mock_gateway, "TestFolder")
    return checker


def test_magic_folder_checker_name(mfc):
    assert mfc.name == "TestFolder"


def test_magic_folder_checker_remote_default_false(mfc):
    assert mfc.remote is False


def test_notify_updated_files(mfc, qtbot):
    mfc.updated_files = [
        {
            "action": "added",
            "cap": "URI:LIT",
            "deleted": False,
            "member": "admin",
            "mtime": 1,
            "path": "file_1.txt",
            "size": 0,
        },
        {
            "action": "added",
            "cap": "URI:LIT",
            "deleted": False,
            "member": "admin",
            "mtime": 2,
            "path": "file_2.txt",
            "size": 0,
        },
    ]
    with qtbot.wait_signal(mfc.files_updated) as blocker:
        mfc.notify_updated_files()
    assert blocker.args == [["file_1.txt", "file_2.txt"], "added", ""]


status_data = [
    {
        "kind": "upload",
        "path": "file_4",
        "percent_done": 0,
        "queued_at": 1,
        "size": 2560,
        "status": "queued",
    },
    {
        "kind": "upload",
        "path": "file_3",
        "percent_done": 0,
        "queued_at": 1,
        "size": None,
        "status": "queued",
    },
    {
        "kind": "upload",
        "path": "file_2",
        "percent_done": 50.0,
        "queued_at": 1,
        "size": 1024,
        "started_at": 1,
        "status": "started",
    },
    {
        "kind": "upload",
        "path": "file_1",
        "percent_done": 100.0,
        "queued_at": 1,
        "size": 512,
        "started_at": 1,
        "status": "success",
        "success_at": 1,
    },
]


def test_emit_transfer_progress_updated(mfc, qtbot):
    with qtbot.wait_signal(mfc.transfer_progress_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [1024, 4096]  # bytes transferred, bytes total


def test_emit_transfer_speed_updated(mfc, monkeypatch, qtbot):
    mfc.sync_time_started = 1
    monkeypatch.setattr("time.time", lambda: 2)  # One second has passed
    with qtbot.wait_signal(mfc.transfer_speed_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [1024]  # bytes per second


def test_emit_transfer_seconds_remaining_updated(mfc, monkeypatch, qtbot):
    mfc.sync_time_started = 1
    monkeypatch.setattr("time.time", lambda: 2)  # One second has passed
    with qtbot.wait_signal(mfc.transfer_seconds_remaining_updated) as blocker:
        mfc.emit_transfer_signals(status_data)
    assert blocker.args == [3]  # seconds remaining


def test_parse_status_set_sync_time_started_by_earliest_time(mfc):
    mfc.parse_status(
        [
            {
                "kind": "upload",
                "path": "two",
                "status": "queued",
                "queued_at": 2,
            },
            {
                "kind": "upload",
                "path": "one",
                "status": "queued",
                "queued_at": 1,
            },
        ]
    )
    assert mfc.sync_time_started == 1


def test_parse_status_return_values_syncing(mfc):
    state, kind, path, failures = mfc.parse_status(status_data)
    assert (state, kind, path, failures) == (1, "upload", "file_2", [])


def test_parse_status_state_up_to_date(mfc):
    mfc.initial_scan_completed = True
    state, _, _, _ = mfc.parse_status({})
    assert state == 2


def test_parse_status_append_failure(mfc):
    task = {"kind": "upload", "status": "failure", "path": "0", "queued_at": 1}
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
    mfc.state = mfc.SYNCING
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.parse_status",
        lambda x, y: (2, "upload", "file_0", []),
    )
    with qtbot.wait_signal(mfc.status_updated) as blocker:
        mfc.process_status(status_data)
    assert blocker.args == [mfc.SCANNING]


def test_process_status_emit_status_updated_up_to_date(
    mfc, monkeypatch, qtbot
):
    mfc.state = mfc.SCANNING
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.parse_status",
        lambda x, y: (2, "upload", "file_0", []),
    )
    with qtbot.wait_signal(mfc.status_updated) as blocker:
        mfc.process_status(status_data)
    assert blocker.args == [mfc.UP_TO_DATE]


def test_process_status_emit_sync_finished(mfc, monkeypatch, qtbot):
    mfc.state = mfc.SCANNING
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.parse_status",
        lambda x, y: (2, "upload", "file_0", []),
    )
    with qtbot.wait_signal(mfc.sync_finished):
        mfc.process_status(status_data)


def test_process_status_emit_sync_started(mfc, monkeypatch, qtbot):
    mfc.state = mfc.SCANNING
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.parse_status",
        lambda x, y: (1, "upload", "file_0", []),
    )
    with qtbot.wait_signal(mfc.sync_started):
        mfc.process_status(status_data)


def test_compare_states_emit_file_updated(mfc, qtbot):
    previous = {}
    current = {
        1234567890.123456: {
            "size": 1024,
            "mtime": 1234567890.123456,
            "deleted": False,
            "cap": "URI:CHK:aaaaaa:bbbbbb:1:1:1024",
            "path": "file_1",
            "member": "admin",
        }
    }
    with qtbot.wait_signal(mfc.file_updated):
        mfc.compare_states(current, previous)


def test_compare_states_file_added(mfc):
    previous = {}
    current = {
        1234567890.123456: {
            "size": 1024,
            "mtime": 1234567890.123456,
            "deleted": False,
            "cap": "URI:CHK:aaaaaa:bbbbbb:1:1:1024",
            "path": "file_1",
            "member": "admin",
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]["action"] == "added"


def test_compare_states_file_updated(mfc):
    previous = {
        1234567890.123456: {
            "size": 1024,
            "mtime": 1234567890.123456,
            "deleted": False,
            "cap": "URI:CHK:aaaaaa:bbbbbb:1:1:1024",
            "path": "file_1",
            "member": "admin",
        }
    }
    current = {
        1234567891.123456: {
            "size": 2048,
            "mtime": 1234567891.123456,
            "deleted": False,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]["action"] == "updated"


def test_compare_states_file_deleted(mfc):
    previous = {
        1234567891.123456: {
            "size": 2048,
            "mtime": 1234567891.123456,
            "deleted": False,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    current = {
        1234567892.123456: {
            "size": 2048,
            "mtime": 1234567892.123456,
            "deleted": True,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]["action"] == "deleted"


def test_compare_states_file_restored(mfc):
    previous = {
        1234567892.123456: {
            "size": 2048,
            "mtime": 1234567892.123456,
            "deleted": True,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    current = {
        1234567893.123456: {
            "size": 2048,
            "mtime": 1234567893.123456,
            "deleted": False,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]["action"] == "restored"


def test_compare_states_directory_created(mfc):
    previous = {
        1234567893.123456: {
            "size": 2048,
            "mtime": 1234567893.123456,
            "deleted": False,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        }
    }
    current = {
        1234567893.123456: {
            "size": 2048,
            "mtime": 1234567893.123456,
            "deleted": False,
            "cap": "URI:CHK:cccccc:dddddd:1:1:2048",
            "path": "file_1",
            "member": "admin",
        },
        1234567894.123456: {
            "size": 0,
            "mtime": 1234567894.123456,
            "deleted": False,
            "cap": "URI:DIR:eeeeee:ffffff",
            "path": "subdir/",
            "member": "admin",
        },
    }
    mfc.compare_states(current, previous)
    assert mfc.updated_files[0]["action"] == "created"


fake_gateway = MagicMock()
fake_gateway.get_magic_folder_state = MagicMock(
    return_value=([("Alice", "URI:DIR2:aaaa:bbbb")], 2048, 9999, {})
)


@inlineCallbacks
def test_do_remote_scan_emit_members_updated(mfc, qtbot):
    mfc.gateway = fake_gateway
    with qtbot.wait_signal(mfc.members_updated) as blocker:
        yield mfc.do_remote_scan()
    assert blocker.args == [[("Alice", "URI:DIR2:aaaa:bbbb")]]


@inlineCallbacks
def test_do_remote_scan_emit_size_updated(mfc, qtbot):
    mfc.gateway = fake_gateway
    with qtbot.wait_signal(mfc.size_updated) as blocker:
        yield mfc.do_remote_scan()
    assert blocker.args == [2048]


@inlineCallbacks
def test_do_remote_scan_emit_mtime_updated(mfc, qtbot):
    mfc.gateway = fake_gateway
    with qtbot.wait_signal(mfc.mtime_updated) as blocker:
        yield mfc.do_remote_scan()
    assert blocker.args == [9999]


@inlineCallbacks
def test_do_check(mfc):
    mfc.gateway = MagicMock()
    mfc.gateway.get_magic_folder_status = MagicMock(return_value={})
    mfc.do_remote_scan = MagicMock()
    yield mfc.do_check()
    assert mfc.do_remote_scan.call_count


@inlineCallbacks
def test_grid_checker_emit_space_updated(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.space_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [1234]


@inlineCallbacks
def test_grid_checker_emit_nodes_updated_(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.nodes_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [8, 10]


@inlineCallbacks
def test_grid_checker_emit_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.connected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_emit_disconnected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(5, 10, 1234))
    gc.is_connected = True
    with qtbot.wait_signal(gc.disconnected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_not_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=0))
    gc.gateway.get_grid_status = MagicMock(return_value=None)
    yield gc.do_check()
    assert gc.num_connected == 0


def test_monitor_add_magic_folder_checker():
    monitor = Monitor(MagicMock())
    monitor.add_magic_folder_checker("TestFolder")
    assert "TestFolder" in monitor.magic_folder_checkers


@inlineCallbacks
def test_monitor_scan_rootcap_no_folders():
    monitor = Monitor(MagicMock())
    monitor.gateway.await_ready = MagicMock(return_value=True)
    monitor.gateway.get_magic_folders_from_rootcap = MagicMock(
        return_value=None
    )
    yield monitor.scan_rootcap()
    assert monitor.magic_folder_checkers == {}


@inlineCallbacks
def test_monitor_scan_rootcap_add_folder(qtbot, monkeypatch):
    monitor = Monitor(MagicMock())
    monitor.gateway.await_ready = MagicMock(return_value=True)
    monitor.gateway.get_magic_folders_from_rootcap = MagicMock(
        return_value={"TestFolder": {"collective_dircap": "URI:DIR2:"}}
    )
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.do_remote_scan",
        lambda x, y: MagicMock(),
    )
    with qtbot.wait_signal(monitor.remote_folder_added) as blocker:
        yield monitor.scan_rootcap("test_overlay.png")
    assert blocker.args == ["TestFolder", "test_overlay.png"]


@inlineCallbacks
def test_monitor_do_checks_add_magic_folder_checker(monkeypatch):
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.do_check", lambda _: MagicMock()
    )
    monitor = Monitor(MagicMock(magic_folders={"TestFolder": {}}))
    monitor.grid_checker = MagicMock()
    yield monitor.do_checks()
    assert "TestFolder" in monitor.magic_folder_checkers


@inlineCallbacks
def test_monitor_do_checks_switch_magic_folder_checker_remote(monkeypatch):
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.do_check", lambda _: MagicMock()
    )
    monitor = Monitor(MagicMock(magic_folders={"TestFolder": {}}))
    monitor.grid_checker = MagicMock()
    test_mfc = MagicFolderChecker(MagicMock(), "TestFolder")
    test_mfc.remote = True
    monitor.magic_folder_checkers = {"TestFolder": test_mfc}
    yield monitor.do_checks()
    assert monitor.magic_folder_checkers["TestFolder"].remote is False


@inlineCallbacks
def test_monitor_emit_check_finished(monkeypatch, qtbot):
    monkeypatch.setattr(
        "gridsync.monitor.MagicFolderChecker.do_check", lambda _: MagicMock()
    )
    monitor = Monitor(MagicMock(magic_folders={"TestFolder": {}}))
    monitor.grid_checker = MagicMock()
    with qtbot.wait_signal(monitor.check_finished):
        yield monitor.do_checks()


def test_monitor_start():
    monitor = Monitor(MagicMock())
    monitor.timer = MagicMock()
    monitor.start()
    assert monitor.timer.mock_calls == [call.start(2, now=True)]


def test_monitor_multiple_start():
    """
    Calling ``Monitor.start`` multiple times has no effects beyond those of
    calling it once.
    """
    monitor = Monitor(MagicMock())
    monitor.timer = MagicMock()
    monitor.start()
    monitor.start()
    assert monitor.timer.mock_calls == [call.start(2, now=True)]
