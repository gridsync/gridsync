import pytest

from gridsync.magic_folder_events import (
    MagicFolderEventHandler,
    MagicFolderOperationsMonitor,
    MagicFolderStatus,
)


def test_magic_folder_event_handler_emits_folder_added_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.folder_added):
        handler.handle({"kind": "folder-added", "folder": "TestFolder"})


def test_magic_folder_event_handler_emits_folder_removed_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.folder_removed):
        handler.handle({"kind": "folder-left", "folder": "TestFolder"})


def test_magic_folder_event_handler_emits_upload_queued_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.upload_queued):
        handler.handle(
            {
                "kind": "upload-queued",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_upload_started_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.upload_started):
        handler.handle(
            {
                "kind": "upload-started",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_upload_finished_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.upload_finished):
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_download_queued_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.download_queued):
        handler.handle(
            {
                "kind": "download-queued",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_download_started_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.download_started):
        handler.handle(
            {
                "kind": "download-started",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_download_finished_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.download_finished):
        handler.handle(
            {
                "kind": "download-finished",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )


def test_magic_folder_event_handler_emits_scan_completed_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.scan_completed):
        handler.handle(
            {"kind": "scan-completed", "folder": "TestFolder", "timestamp": 1}
        )


def test_magic_folder_event_handler_emits_poll_completed_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.poll_completed):
        handler.handle(
            {"kind": "poll-completed", "folder": "TestFolder", "timestamp": 1}
        )


def test_magic_folder_event_handler_emits_error_occurred_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.error_occurred):
        handler.handle(
            {
                "kind": "error-occurred",
                "folder": "TestFolder",
                "summary": "Test error message",
                "timestamp": 1,
            }
        )


def test_magic_folder_event_handler_emits_connection_changed_signal(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.connection_changed):
        handler.handle(
            {
                "kind": "tahoe-connection-changed",
                "connected": 1,
                "desired": 1,
                "happy": True,
            }
        )


def test_magic_folder_operations_monitor_default_loading_status():
    monitor = MagicFolderOperationsMonitor(MagicFolderEventHandler())
    assert monitor.get_status("TestFolder") == MagicFolderStatus.LOADING


def test_folder_status_changed_signal_syncing(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.folder_status_changed) as blocker:
        handler.handle(
            {
                "kind": "upload-started",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )
    assert blocker.args == ["TestFolder", MagicFolderStatus.SYNCING]


def test_folder_status_changed_signal_up_to_date(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-started",
            "folder": "TestFolder",
            "relpath": "test.txt",
        }
    )
    with qtbot.wait_signal(handler.folder_status_changed) as blocker:
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )
    assert blocker.args == ["TestFolder", MagicFolderStatus.UP_TO_DATE]


def test_folder_status_changed_signal_error(qtbot):
    handler = MagicFolderEventHandler()
    with qtbot.wait_signal(handler.folder_status_changed) as blocker:
        handler.handle(
            {
                "kind": "error-occurred",
                "folder": "TestFolder",
                "summary": "Test error message",
                "timestamp": 1,
            }
        )
    assert blocker.args == ["TestFolder", MagicFolderStatus.ERROR]


def test_overall_status_changed_signal_syncing(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "test.txt",
        }
    )
    with qtbot.wait_signal(handler.overall_status_changed) as blocker:
        handler.handle(
            {
                "kind": "upload-started",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )
    assert blocker.args == [MagicFolderStatus.SYNCING]


def test_overall_status_changed_signal_error(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "test.txt",
        }
    )
    with qtbot.wait_signal(handler.overall_status_changed) as blocker:
        handler.handle(
            {
                "kind": "error-occurred",
                "folder": "TestFolder",
                "summary": "Test error message",
                "timestamp": 1,
            }
        )
    assert blocker.args == [MagicFolderStatus.ERROR]


def test_overall_status_changed_signal_up_to_date(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "test.txt",
        }
    )
    with qtbot.wait_signal(handler.overall_status_changed) as blocker:
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "test.txt",
            }
        )
    assert blocker.args == [MagicFolderStatus.UP_TO_DATE]


def test_sync_progress_updated_signal(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "File1",
        }
    )
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "File2",
        }
    )
    with qtbot.wait_signal(handler.sync_progress_updated) as blocker:
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "File1",
            }
        )
    assert blocker.args == ["TestFolder", 1, 2]  # 1/2 files uploaded


def test_files_updated_signal(qtbot):
    handler = MagicFolderEventHandler()
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "File1",
        }
    )
    handler.handle(
        {
            "kind": "upload-queued",
            "folder": "TestFolder",
            "relpath": "File2",
        }
    )
    with qtbot.wait_signal(handler.files_updated) as blocker:
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "File1",
            }
        )
        handler.handle(
            {
                "kind": "upload-finished",
                "folder": "TestFolder",
                "relpath": "File2",
            }
        )
    assert blocker.args == ["TestFolder", ["File1", "File2"]]
