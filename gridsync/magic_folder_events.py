from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from enum import Enum, auto

from qtpy.QtCore import QObject, Signal, Slot

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
        self._last_scans: defaultdict[str, float] = defaultdict(float)
        self._last_polls: defaultdict[str, float] = defaultdict(float)

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
        elif not self._last_scans[folder] or not self._last_polls[folder]:
            # A folder should not be considered "up to date" until it
            # has completed at least one scan and one poll.
            return
        else:
            status = MagicFolderStatus.UP_TO_DATE
        if self._statuses[folder] != status:
            self._statuses[folder] = status
            self.event_handler.folder_status_changed.emit(folder, status)
            self._update_overall_status()

    @Slot(str, str)
    def on_upload_started(self, folder: str, relpath: str) -> None:
        self._uploads[folder].append(relpath)
        self._update_status(folder)

    @Slot(str, str)
    def on_upload_finished(self, folder: str, relpath: str) -> None:
        try:
            self._uploads[folder].remove(relpath)
        except ValueError:
            pass
        self._update_status(folder)

    @Slot(str, str)
    def on_download_started(self, folder: str, relpath: str) -> None:
        self._downloads[folder].append(relpath)
        self._update_status(folder)

    @Slot(str, str)
    def on_download_finished(self, folder: str, relpath: str) -> None:
        try:
            self._downloads[folder].remove(relpath)
        except ValueError:
            pass
        self._update_status(folder)

    @Slot(str, str, float)
    def on_error_occurred(self, folder: str, summary: str, _: float) -> None:
        self._errors[folder].append(summary)
        self._update_status(folder)

    @Slot(str, float)
    def on_scan_completed(self, folder: str, timestamp: float) -> None:
        self._last_scans[folder] = timestamp
        self._update_status(folder)

    @Slot(str, float)
    def on_poll_completed(self, folder: str, timestamp: float) -> None:
        self._last_polls[folder] = timestamp
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

    @Slot(str, str)
    def on_upload_queued(self, folder: str, relpath: str) -> None:
        self._queued[folder].append(relpath)
        self._update_progress(folder)

    @Slot(str, str)
    def on_upload_finished(self, folder: str, relpath: str) -> None:
        self._finished[folder].append(relpath)
        self._update_progress(folder)

    @Slot(str, str)
    def on_download_queued(self, folder: str, relpath: str) -> None:
        self._queued[folder].append(relpath)
        self._update_progress(folder)

    @Slot(str, str)
    def on_download_finished(self, folder: str, relpath: str) -> None:
        self._finished[folder].append(relpath)
        self._update_progress(folder)


class MagicFolderEventHandler(QObject):
    folder_added = Signal(str)  # folder_name
    folder_removed = Signal(str)  # folder_name

    upload_queued = Signal(str, str)  # folder_name, relpath
    upload_started = Signal(str, str)  # folder_name, relpath
    upload_finished = Signal(str, str, float)  # folder_name, relpath, time

    download_queued = Signal(str, str)  # folder_name, relpath
    download_started = Signal(str, str)  # folder_name, relpath
    download_finished = Signal(str, str, float)  # folder_name, relpath, time

    error_occurred = Signal(str, str, int)  # folder_name, summary, timestamp

    scan_completed = Signal(str, float)  # folder_name, last_scan
    poll_completed = Signal(str, float)  # folder_name, last_poll
    connection_changed = Signal(int, int, bool)  # connected, desired, happy

    invite_created = Signal(
        str, str, str, str
    )  # folder, uuid, participant-name, mode
    invite_welcomed = Signal(
        str, str, str, str, dict
    )  # folder, uuid, participant-name, mode, welcome
    invite_code_created = Signal(
        str, str, str, str, str
    )  # folder, uuid, participant-name, mode, code
    invite_versions_received = Signal(
        str, str, str, str, dict
    )  # folder, uuid, participant-name, mode, versions
    invite_succeeded = Signal(
        str, str, str, str
    )  # folder, uuid, participant-name, mode
    invite_failed = Signal(
        str, str, str, str, str
    )  # folder, uuid, participant-name, mode, reason
    invite_rejected = Signal(
        str, str, str, str, str
    )  # folder, uuid, participant-name, mode, reason
    invite_cancelled = Signal(
        str, str, str, str
    )  # folder, uuid, participant-name, mode

    # From MagicFolderOperationsMonitor
    folder_status_changed = Signal(str, object)  # folder, MagicFolderStatus
    overall_status_changed = Signal(object)  # MagicFolderStatus

    # From MagicFolderProgressMonitor
    sync_progress_updated = Signal(str, object, object)  # folder, cur, total
    files_updated = Signal(str, list)  # folder, files

    def __init__(self) -> None:
        super().__init__()

        _om = MagicFolderOperationsMonitor(self)
        self.upload_started.connect(lambda f, p: _om.on_upload_started(f, p))
        self.upload_finished.connect(lambda f, p: _om.on_upload_finished(f, p))
        self.download_started.connect(
            lambda f, p: _om.on_download_started(f, p)
        )
        self.download_finished.connect(
            lambda f, p: _om.on_download_finished(f, p)
        )
        self.error_occurred.connect(
            lambda f, s, t: _om.on_error_occurred(f, s, t)
        )
        self.scan_completed.connect(lambda f, t: _om.on_scan_completed(f, t))
        self.poll_completed.connect(lambda f, t: _om.on_poll_completed(f, t))
        self.operations_monitor = _om

        _pm = MagicFolderProgressMonitor(self)
        self.upload_queued.connect(lambda f, p: _pm.on_upload_queued(f, p))
        self.upload_finished.connect(lambda f, p: _pm.on_upload_finished(f, p))
        self.download_queued.connect(lambda f, p: _pm.on_download_queued(f, p))
        self.download_finished.connect(
            lambda f, p: _pm.on_download_finished(f, p)
        )
        self.progress_monitor = _pm

    def handle(self, event: dict) -> None:  # noqa: C901 [max-complexity]
        folder = event.get("folder", "")
        timestamp = float(event.get("timestamp", time.time()))
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
                self.upload_finished.emit(folder, relpath, timestamp)
            case {"kind": "download-queued", "relpath": relpath}:
                self.download_queued.emit(folder, relpath)
            case {"kind": "download-started", "relpath": relpath}:
                self.download_started.emit(folder, relpath)
            case {"kind": "download-finished", "relpath": relpath}:
                self.download_finished.emit(folder, relpath, timestamp)
            case {"kind": "scan-completed"}:
                self.scan_completed.emit(folder, timestamp)
            case {"kind": "poll-completed"}:
                self.poll_completed.emit(folder, timestamp)
            case {"kind": "error-occurred", "summary": summary}:
                self.error_occurred.emit(folder, summary, timestamp)
            case {
                "kind": "tahoe-connection-changed",
                "connected": connected,
                "desired": desired,
                "happy": happy,
            }:
                self.connection_changed.emit(connected, desired, happy)
            case {
                "kind": "invite-created",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
            }:
                self.invite_created.emit(folder, uuid, participant_name, mode)
            case {
                "kind": "invite-welcomed",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
                "welcome": welcome,
            }:
                self.invite_welcomed.emit(
                    folder, uuid, participant_name, mode, welcome
                )
            case {
                "kind": "invite-code-created",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
                "code": code,
            }:
                self.invite_code_created.emit(
                    folder, uuid, participant_name, mode, code
                )
            case {
                "kind": "invite-versions-received",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
                "versions": versions,
            }:
                self.invite_versions_received.emit(
                    folder, uuid, participant_name, mode, versions
                )
            case {
                "kind": "invite-succeeded",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
            }:
                self.invite_succeeded.emit(
                    folder, uuid, participant_name, mode
                )
            case {
                "kind": "invite-failed",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
                "reason": reason,
            }:
                self.invite_failed.emit(
                    folder, uuid, participant_name, mode, reason
                )
            case {
                "kind": "invite-rejected",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
                "reason": reason,
            }:
                self.invite_rejected.emit(
                    folder, uuid, participant_name, mode, reason
                )
            case {
                "kind": "invite-cancelled",
                "id": uuid,
                "participant-name": participant_name,
                "mode": mode,
            }:
                self.invite_cancelled.emit(
                    folder, uuid, participant_name, mode
                )
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
