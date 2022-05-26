from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from atomicwrites import atomic_write
from twisted.internet.defer import DeferredLock, inlineCallbacks

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred


class RootcapManager:
    def __init__(self, gateway: Tahoe, basedir: str = "v0") -> None:
        self.gateway = gateway
        self.basedir = basedir
        self.lock = DeferredLock()
        self._rootcap_path = Path(gateway.nodedir, "private", "rootcap")
        self._rootcap: str = ""
        self._basedircap = ""
        self._backup_caps: dict = {}

    def get_rootcap(self) -> str:
        if self._rootcap:
            return self._rootcap
        try:
            self._rootcap = self._rootcap_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        return self._rootcap

    def set_rootcap(self, cap: str, overwrite: bool = False) -> None:
        with atomic_write(
            str(self._rootcap_path), mode="w", overwrite=overwrite
        ) as f:
            f.write(cap)
        logging.debug("Rootcap saved to file: %s", self._rootcap_path)
        self._rootcap = cap

    @inlineCallbacks
    def create_rootcap(self) -> TwistedDeferred[str]:
        logging.debug("Creating rootcap...")
        if self._rootcap_path.exists():
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return self.get_rootcap()
        yield self.lock.acquire()
        try:
            rootcap = yield self.gateway.mkdir()
        finally:
            yield self.lock.release()  # type: ignore
        yield self.lock.acquire()
        if self._rootcap:
            logging.warning("Rootcap already exists")
            yield self.lock.release()  # type: ignore
            return self._rootcap
        try:
            self.set_rootcap(rootcap)
        except FileExistsError:
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return self.get_rootcap()
        finally:
            yield self.lock.release()  # type: ignore
        logging.debug("Rootcap successfully created")
        return self._rootcap

    @inlineCallbacks
    def _get_basedircap(self) -> TwistedDeferred[str]:
        if self._basedircap:
            return self._basedircap
        rootcap = self.get_rootcap()
        if not rootcap:
            rootcap = yield self.create_rootcap()
        subdirs = yield self.gateway.ls(rootcap, exclude_filenodes=True)
        self._basedircap = subdirs.get(self.basedir, {}).get("cap", "")
        if self._basedircap:
            return self._basedircap
        yield self.lock.acquire()
        if self._basedircap:
            yield self.lock.release()  # type: ignore
            return self._basedircap
        logging.debug('Creating base ("%s") dircap...', self.basedir)
        try:
            self._basedircap = yield self.gateway.mkdir(rootcap, self.basedir)
        finally:
            yield self.lock.release()  # type: ignore
        logging.debug('Base ("%s") dircap successfully created', self.basedir)
        return self._basedircap

    @inlineCallbacks
    def create_backup_cap(
        self, name: str, basedircap: str = ""
    ) -> TwistedDeferred[str]:
        if not basedircap:
            basedircap = yield self._get_basedircap()
        yield self.lock.acquire()
        try:
            backup_cap = yield self.gateway.mkdir(basedircap, name)
        finally:
            yield self.lock.release()  # type: ignore
        self._backup_caps[name] = backup_cap
        return backup_cap

    @inlineCallbacks
    def get_backup_cap(
        self, name: str, basedircap: str = ""
    ) -> TwistedDeferred[str]:
        backup_cap = self._backup_caps.get(name)
        if backup_cap:
            return backup_cap
        if not basedircap:
            basedircap = yield self._get_basedircap()
        ls_output = yield self.gateway.ls(basedircap, exclude_filenodes=True)
        backup_caps = {}
        for dirname, data in ls_output.items():
            backup_caps[dirname] = data.get("cap", "")
        backup_cap = backup_caps.get(name, "")
        if not backup_cap:
            backup_cap = yield self.create_backup_cap(name, basedircap)
            backup_caps[name] = backup_cap
        self._backup_caps = backup_caps
        return backup_cap

    @inlineCallbacks
    def add_backup(
        self, dirname: str, name: str, cap: str
    ) -> TwistedDeferred[str]:
        backup_cap = yield self.get_backup_cap(dirname)
        yield self.lock.acquire()
        try:
            cap = yield self.gateway.link(backup_cap, name, cap)
        finally:
            yield self.lock.release()  # type: ignore
        return cap

    @inlineCallbacks
    def get_backup(self, dirname: str, name: str) -> TwistedDeferred[str]:
        """
        Retrieve a backup previously added with `add_backup`.

        :param dirname: same meaning as add_backup
        :param name: same meaning as add_backup
        """
        backup_cap = yield self.get_backup_cap(dirname)
        ls_output = yield self.gateway.ls(backup_cap)
        for dirname, data in ls_output.items():
            if dirname == name:
                return data.get("ro_cap", data.get("cap", {}))
        raise ValueError(f"Backup not found for {dirname} -> {name}")

    @inlineCallbacks
    def get_backups(self, dirname: str) -> TwistedDeferred[Optional[dict]]:
        backup_cap = yield self.get_backup_cap(dirname)
        ls_output = yield self.gateway.ls(backup_cap)
        return ls_output

    @inlineCallbacks
    def remove_backup(self, dirname: str, name: str) -> TwistedDeferred[None]:
        backup_cap = yield self.get_backup_cap(dirname)
        yield self.lock.acquire()
        try:
            yield self.gateway.unlink(backup_cap, name, missing_ok=True)
        finally:
            yield self.lock.release()  # type: ignore
