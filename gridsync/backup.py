from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict

from atomicwrites import atomic_write
from twisted.internet.defer import inlineCallbacks

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred


class BackupManager:
    def __init__(self, gateway: Tahoe) -> None:
        self.gateway = gateway
        self._lock = gateway.lock
        self._rootcap_path = Path(gateway.nodedir, "private", "rootcap")
        self._rootcap: str = ""

    def get_rootcap(self) -> str:
        if self._rootcap:
            return self._rootcap
        try:
            self._rootcap = self._rootcap_path.read_text()
        except FileNotFoundError:
            return ""
        return self._rootcap

    def set_rootcap(self, cap: str) -> None:
        with atomic_write(str(self._rootcap_path), mode="w") as f:
            f.write(cap)
        logging.debug("Rootcap saved to file: %s", self._rootcap_path)
        self._rootcap = cap

    @inlineCallbacks
    def create_rootcap(self) -> TwistedDeferred[str]:
        logging.debug("Creating rootcap...")
        if self._rootcap_path.exists():
            raise OSError(f"Rootcap file already exists: {self._rootcap_path}")
        yield self._lock.acquire()
        rootcap = yield self.gateway.mkdir()
        try:
            self.set_rootcap(rootcap)
        except FileExistsError:
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return self.get_rootcap()
        finally:
            yield self._lock.release()
        return self._rootcap
