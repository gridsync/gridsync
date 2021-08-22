from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict

from PyQt5.QtCore import QObject, pyqtSignal
from watchdog.events import DirModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import ObservedWatch


class _WatchdogEventHandler(FileSystemEventHandler):
    def __init__(self, watchdog: Watchdog):
        super().__init__()
        self._watchdog = watchdog

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._watchdog.on_event(event)


class Watchdog(QObject):

    directory_modified = pyqtSignal(str)  # src_path

    def __init__(self) -> None:
        super().__init__()
        self._observer = Observer()
        self._event_handler = _WatchdogEventHandler(self)
        self._watches: Dict[str, ObservedWatch] = {}

    def on_event(self, event: FileSystemEvent) -> None:
        if isinstance(event, DirModifiedEvent):
            self.directory_modified.emit(event.src_path)

    def add_watch(self, path: str) -> None:
        logging.debug("Scheduling watch for %s...", path)
        try:
            self._watches[path] = self._observer.schedule(
                self._event_handler, path, recursive=True
            )
        except FileNotFoundError:
            logging.warning(
                "Cannot schedule watch for missing path; returning"
            )
            return
        logging.debug("Watch scheduled for %s", path)

    def remove_watch(self, path: str) -> None:
        logging.debug("Unscheduling watch for %s...", path)
        try:
            self._observer.unschedule(self._watches.get(path))
        except (FileNotFoundError, KeyError):
            logging.warning(
                "Cannot unschedule watch for missing path; returning"
            )
            return
        try:
            del self._watches[path]
        except KeyError:
            pass
        logging.debug("Watch unscheduled for %s", path)

    def stop(self) -> None:
        logging.debug("Stopping Watchdog...")
        self._observer.unschedule_all()
        self._observer.stop()
        try:
            self._observer.join()
        except RuntimeError:
            pass
        logging.debug("Watchdog stopped.")

    def start(self) -> None:
        logging.debug("Starting Watchdog...")
        try:
            self._observer.start()
        except RuntimeError:
            pass
        logging.debug("Watchdog started.")