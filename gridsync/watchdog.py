from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import QObject, Signal
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    from watchdog.events import FileSystemEvent
    from watchdog.observers.api import ObservedWatch


class _WatchdogEventHandler(FileSystemEventHandler):
    def __init__(self, watchdog: Watchdog, path: str):
        super().__init__()
        self._watchdog = watchdog
        self._path = path

    def on_any_event(self, event: FileSystemEvent) -> None:
        self._watchdog.path_modified.emit(self._path)


class Watchdog(QObject):
    path_modified = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._observer = Observer()
        self._watches: dict[str, ObservedWatch] = {}

    def add_watch(self, path: str) -> None:
        logging.debug("Scheduling watch for %s...", path)
        self._watches[path] = self._observer.schedule(
            _WatchdogEventHandler(self, path), path, recursive=True
        )
        logging.debug("Watch scheduled for %s", path)

    def remove_watch(self, path: str) -> None:
        logging.debug("Unscheduling watch for %s...", path)
        watch = self._watches.get(path)
        if watch is None:
            logging.warning("No watch found for %s", path)
            return
        self._observer.unschedule(watch)
        try:
            del self._watches[path]
        except KeyError:
            pass
        logging.debug("Watch unscheduled for %s", path)

    def stop(self) -> None:
        if not self._observer.is_alive():
            logging.warning("Tried to stop Watchdog that wasn't started.")
            return
        logging.debug("Stopping Watchdog...")
        self._observer.stop()
        try:
            self._observer.join()
        except RuntimeError:
            pass
        logging.debug("Watchdog stopped.")

    def start(self) -> None:
        if self._observer.is_alive():
            logging.warning("Tried to start Watchdog that was already started")
            return
        logging.debug("Starting Watchdog...")
        try:
            self._observer.start()
        except RuntimeError:
            pass
        logging.debug("Watchdog started.")
