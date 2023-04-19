from __future__ import annotations

from collections import defaultdict
from enum import Enum, auto

from qtpy.QtCore import QObject, Signal


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
            status = MagicFolderStatus.SYNCING
        elif MagicFolderStatus.ERROR in statuses:  # At least one has an error
            status = MagicFolderStatus.ERROR
        elif statuses == {MagicFolderStatus.UP_TO_DATE}:  # All are up-to-date
            status = MagicFolderStatus.UP_TO_DATE
        else:
            status = MagicFolderStatus.WAITING
        self.event_handler.overall_status_changed.emit(status)

    def _update_status(self, folder: str) -> MagicFolderStatus | None:
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
            return status

    def add_upload(
        self, folder: str, relpath: str
    ) -> MagicFolderStatus | None:
        self._uploads[folder].append(relpath)
        return self._update_status(folder)

    def remove_upload(
        self, folder: str, relpath: str
    ) -> MagicFolderStatus | None:
        try:
            self._uploads[folder].remove(relpath)
        except ValueError:
            pass
        return self._update_status(folder)

    def add_download(
        self, folder: str, relpath: str
    ) -> MagicFolderStatus | None:
        self._downloads[folder].append(relpath)
        return self._update_status(folder)

    def remove_download(
        self, folder: str, relpath: str
    ) -> MagicFolderStatus | None:
        try:
            self._downloads[folder].remove(relpath)
        except ValueError:
            pass
        return self._update_status(folder)

    def add_error(self, folder: str, summary: str) -> MagicFolderStatus | None:
        self._errors[folder].append(summary)
        return self._update_status(folder)

    def remove_error(
        self, folder: str, summary: str
    ) -> MagicFolderStatus | None:
        try:
            self._errors[folder].remove(summary)
        except ValueError:
            pass
        return self._update_status(folder)


class MagicFolderEventHandler(QObject):
    folder_added = Signal(str)  # folder_name
    folder_removed = Signal(str)  # folder_name

    upload_queued = Signal(str, str)  # folder_name, relpath
    upload_started = Signal(str, str, dict)  # folder_name, relpath, data
    upload_finished = Signal(str, str, dict)  # folder_name, relpath, data

    download_queued = Signal(str, str)  # folder_name, relpath
    download_started = Signal(str, str, dict)  # folder_name, relpath, data
    download_finished = Signal(str, str, dict)  # folder_name, relpath, data

    error_occurred = Signal(str, str, int)  # folder_name, summary, timestamp

    scan_completed = Signal(str, float)  # folder_name, last_scan
    poll_completed = Signal(str, float)  # folder_name, last_poll
    connection_changed = Signal(int, int, bool)  # connected, desired, happy
    #
    folder_status_changed = Signal(str, object)  # folder, MagicFolderStatus
    overall_status_changed = Signal(object)  # MagicFolderStatus

    def __init__(self) -> None:
        super().__init__()

        self._operations_monitor = MagicFolderOperationsMonitor(self)
        self.upload_started.connect(self._operations_monitor.add_upload)
        self.upload_finished.connect(self._operations_monitor.remove_upload)
        self.download_started.connect(self._operations_monitor.add_download)
        self.download_finished.connect(
            self._operations_monitor.remove_download
        )
        self.error_occurred.connect(self._operations_monitor.add_error)

    def handle(self, event: dict) -> None:
        from pprint import pprint

        pprint(event)  # XXX
        folder = event.get("folder", "")
        match event:
            case {"kind": "folder-added"}:
                self.folder_added.emit(folder)
            case {"kind": "folder-left"}:
                self.folder_removed.emit(folder)
            case {"kind": "upload-queued", "relpath": relpath}:
                self.upload_queued.emit(folder, relpath)
            case {"kind": "upload-started", "relpath": relpath}:
                self.upload_started.emit(folder, relpath, {})
            case {"kind": "upload-finished", "relpath": relpath}:
                self.upload_finished.emit(folder, relpath, {})
            case {"kind": "download-queued", "relpath": relpath}:
                self.download_queued.emit(folder, relpath)
            case {"kind": "download-started", "relpath": relpath}:
                self.download_started.emit(folder, relpath, {})
            case {"kind": "download-finished", "relpath": relpath}:
                self.download_finished.emit(folder, relpath, {})
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
