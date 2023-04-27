from __future__ import annotations

import json
import logging
from collections import defaultdict
from enum import Enum, auto

from qtpy.QtCore import QObject, Signal

from gridsync.websocket import WebSocketReaderService


class MagicFolderStatus(Enum):
    LOADING = auto()
    SYNCING = auto()
    UP_TO_DATE = auto()
    ERROR = auto()
    STORED_REMOTELY = auto()
    WAITING = auto()


class MagicFolderOperationsMonitor:
    def __init__(self, event_handler: MagicFolderEventHandler) -> None:
        self.event_handler = event_handler

        self._uploads: defaultdict[str, list] = defaultdict(list)
        self._downloads: defaultdict[str, list] = defaultdict(list)
        self._errors: defaultdict[str, list] = defaultdict(list)
        self._statuses: defaultdict[str, MagicFolderStatus] = defaultdict(
            lambda: MagicFolderStatus.LOADING
        )

    def get_status(self, folder_name: str) -> MagicFolderStatus:
        return self._statuses[folder_name]

    def _update_overall_status(self) -> None:
        statuses = set(self._statuses.values())
        if MagicFolderStatus.SYNCING in statuses:  # At least one is syncing
            self.event_handler.overall_status_changed.emit(
                MagicFolderStatus.SYNCING
            )
        elif MagicFolderStatus.ERROR in statuses:  # At least one has an error
            self.event_handler.overall_status_changed.emit(
                MagicFolderStatus.ERROR
            )
        elif statuses == {MagicFolderStatus.UP_TO_DATE}:  # All are up-to-date
            self.event_handler.overall_status_changed.emit(
                MagicFolderStatus.UP_TO_DATE
            )

    def _update_status(self, folder: str) -> None:
        if self._uploads[folder] or self._downloads[folder]:
            status = MagicFolderStatus.SYNCING
        elif self._errors[folder]:
            status = MagicFolderStatus.ERROR
        else:
            status = MagicFolderStatus.UP_TO_DATE
        if self._statuses[folder] != status:
            self._statuses[folder] = status
            self.event_handler.folder_status_changed.emit(folder, status)
            self._update_overall_status()

    def on_upload_started(self, folder: str, relpath: str) -> None:
        self._uploads[folder].append(relpath)
        self._update_status(folder)

    def on_upload_finished(self, folder: str, relpath: str) -> None:
        try:
            self._uploads[folder].remove(relpath)
        except ValueError:
            pass
        self._update_status(folder)

    def on_download_started(self, folder: str, relpath: str) -> None:
        self._downloads[folder].append(relpath)
        self._update_status(folder)

    def on_download_finished(self, folder: str, relpath: str) -> None:
        try:
            self._downloads[folder].remove(relpath)
        except ValueError:
            pass
        self._update_status(folder)

    def on_error_occurred(self, folder: str, summary: str) -> None:
        self._errors[folder].append(summary)
        self._update_status(folder)


class MagicFolderProgressMonitor:
    def __init__(self, event_handler: MagicFolderEventHandler) -> None:
        self.event_handler = event_handler

        self._queued: defaultdict[str, list] = defaultdict(list)
        self._finished: defaultdict[str, list] = defaultdict(list)

    def _update_progress(self, folder: str) -> None:
        files = self._finished[folder]
        current = len(files)
        total = len(self._queued[folder])
        self.event_handler.sync_progress_updated.emit(folder, current, total)
        if total and current == total:  # 100%
            self._queued[folder] = []
            self._finished[folder] = []
            self.event_handler.files_updated.emit(folder, files)

    def on_upload_queued(self, folder: str, relpath: str) -> None:
        self._queued[folder].append(relpath)
        self._update_progress(folder)

    def on_upload_finished(self, folder: str, relpath: str) -> None:
        self._finished[folder].append(relpath)
        self._update_progress(folder)

    def on_download_queued(self, folder: str, relpath: str) -> None:
        self._queued[folder].append(relpath)
        self._update_progress(folder)

    def on_download_finished(self, folder: str, relpath: str) -> None:
        self._finished[folder].append(relpath)
        self._update_progress(folder)


class MagicFolderEventHandler(QObject):
    folder_added = Signal(str)  # folder_name
    folder_removed = Signal(str)  # folder_name

    upload_queued = Signal(str, str)  # folder_name, relpath
    upload_started = Signal(str, str)  # folder_name, relpath
    upload_finished = Signal(str, str)  # folder_name, relpath

    download_queued = Signal(str, str)  # folder_name, relpath
    download_started = Signal(str, str)  # folder_name, relpath
    download_finished = Signal(str, str)  # folder_name, relpath

    error_occurred = Signal(str, str, int)  # folder_name, summary, timestamp

    scan_completed = Signal(str, float)  # folder_name, last_scan
    poll_completed = Signal(str, float)  # folder_name, last_poll
    connection_changed = Signal(int, int, bool)  # connected, desired, happy

    # From MagicFolderOperationsMonitor
    folder_status_changed = Signal(str, object)  # folder, MagicFolderStatus
    overall_status_changed = Signal(object)  # MagicFolderStatus

    # From MagicFolderProgressMonitor
    sync_progress_updated = Signal(str, object, object)  # folder, cur, total
    files_updated = Signal(str, list)  # folder, files

    def __init__(self) -> None:
        super().__init__()

        self._operations_monitor = MagicFolderOperationsMonitor(self)
        self.upload_started.connect(self._operations_monitor.on_upload_started)
        self.upload_finished.connect(
            self._operations_monitor.on_upload_finished
        )
        self.download_started.connect(
            self._operations_monitor.on_download_started
        )
        self.download_finished.connect(
            self._operations_monitor.on_download_finished
        )
        self.error_occurred.connect(self._operations_monitor.on_error_occurred)

        self._progress_monitor = MagicFolderProgressMonitor(self)
        self.upload_queued.connect(self._progress_monitor.on_upload_queued)
        self.upload_finished.connect(self._progress_monitor.on_upload_finished)
        self.download_queued.connect(self._progress_monitor.on_download_queued)
        self.download_finished.connect(
            self._progress_monitor.on_download_finished
        )

    def handle(self, event: dict) -> None:
        print(event)  # XXX
        folder = event.get("folder", "")
        match event:
            case {"kind": "folder-added"}:
                self.folder_added.emit(folder)
            case {"kind": "folder-left"}:
                self.folder_removed.emit(folder)
            case {"kind": "upload-queued", "relpath": relpath}:
                self.upload_queued.emit(folder, relpath)
            case {"kind": "upload-started", "relpath": relpath}:
                self.upload_started.emit(folder, relpath)
            case {"kind": "upload-finished", "relpath": relpath}:
                self.upload_finished.emit(folder, relpath)
            case {"kind": "download-queued", "relpath": relpath}:
                self.download_queued.emit(folder, relpath)
            case {"kind": "download-started", "relpath": relpath}:
                self.download_started.emit(folder, relpath)
            case {"kind": "download-finished", "relpath": relpath}:
                self.download_finished.emit(folder, relpath)
            case {"kind": "scan-completed", "timestamp": timestamp}:
                self.scan_completed.emit(folder, timestamp)
            case {"kind": "poll-completed", "timestamp": timestamp}:
                self.poll_completed.emit(folder, timestamp)
            case {
                "kind": "error-occurred",
                "summary": summary,
                "timestamp": timestamp,
            }:
                self.error_occurred.emit(folder, summary, timestamp)
            case {
                "kind": "tahoe-connection-changed",
                "connected": connected,
                "desired": desired,
                "happy": happy,
            }:
                self.connection_changed.emit(connected, desired, happy)
            case _:
                logging.warning('Received unknown event kind: "%s"', event)


class MagicFolderEventsMonitor:
    def __init__(self, event_handler: MagicFolderEventHandler) -> None:
        self.event_handler = event_handler

        self._ws_reader: WebSocketReaderService | None = None

    def _on_status_message_received(self, message: str) -> None:
        data = json.loads(message)
        events = data.get("events", [])
        if not events:
            logging.warning(
                'Received status message with no events: "%s"', data
            )
        for event in events:
            self.event_handler.handle(event)

    def start(self, api_port: int, api_token: str) -> None:
        if self._ws_reader is not None:
            self._ws_reader.stop()
            self._ws_reader = None
        self._ws_reader = WebSocketReaderService(
            f"ws://127.0.0.1:{api_port}/v1/status",
            headers={"Authorization": f"Bearer {api_token}"},
            collector=self._on_status_message_received,
        )
        self._ws_reader.start()

    def stop(self) -> None:
        if self._ws_reader is not None:
            self._ws_reader.stop()
            self._ws_reader = None
