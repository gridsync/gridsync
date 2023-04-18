import pytest

from gridsync.magic_folder import MagicFolderEventHandler


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
