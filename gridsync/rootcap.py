from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from atomicwrites import atomic_write
from tahoe_capabilities import (
    DirectoryWriteCapability,
    danger_real_capability_string,
    writeable_directory_from_string,
)
from twisted.internet.defer import DeferredLock

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class RootcapManager:
    """
    The RootcapManager provides an interface for adding and retrieving
    objects to and from a Tahoe-LAFS root capability -- or "rootcap".

    In Gridsync, the rootcap is intended to provide a central in-grid
    directory into which all other important capabilities are added; by
    preserving their Gridsync rootcap, users preserve any/all other
    important capabilities that have been linked beneath it, making it
    easier to backup and restore access to important on-grid resources.

    The RootcapManager, accordingly, provides higher-level methods for
    adding and retrieving Tahoe-LAFS capabilities to/from the rootcap
    as well as some extra convenience- and safety-related functionality
    not found in lower-level components (such as automatically creating
    paths that don't exist and guarding against simultaneous writes).

    Currently, Gridsync uses RootcapManager to add capabilities from
    magic-folder and zkapauthorizer into the rootcap -- and embeds that
    rootcap into the "Recovery Key" -- thereby allowing users to back
    up and restore access to previously-joined magic-folders (and
    previously-obtained ZKAPs) as part of the user-facing "Restore from
    Recovery Key" flow.
    """

    def __init__(self, gateway: Tahoe, basedir: str = "v0") -> None:
        self.gateway = gateway
        self.basedir = basedir
        self.lock = DeferredLock()
        self._rootcap_path = Path(gateway.nodedir, "private", "rootcap")
        self._rootcap: Optional[DirectoryWriteCapability] = None
        self._basedircap = ""
        self._backup_caps: dict = {}

    def get_rootcap(self) -> Optional[DirectoryWriteCapability]:
        if self._rootcap:
            return self._rootcap
        try:
            rootcap_str = self._rootcap_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        self._rootcap = writeable_directory_from_string(rootcap_str)
        return self._rootcap

    def set_rootcap(
        self, cap: DirectoryWriteCapability, overwrite: bool = False
    ) -> None:
        with atomic_write(
            str(self._rootcap_path), mode="w", overwrite=overwrite
        ) as f:
            f.write(danger_real_capability_string(cap))
        logging.debug("Rootcap saved to file: %s", self._rootcap_path)
        self._rootcap = cap

    async def create_rootcap(self) -> DirectoryWriteCapability:
        await self.lock.acquire()
        try:
            logging.debug("Creating rootcap...")
            rootcap = self.get_rootcap()
            if rootcap is None:
                rootcap = writeable_directory_from_string(
                    (await self.gateway.mkdir())
                )
                self.set_rootcap(rootcap)
                return rootcap
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return rootcap
        finally:
            self.lock.release()

    async def _get_basedircap(self) -> str:
        if self._basedircap:
            return self._basedircap
        rootcap = self.get_rootcap()
        if rootcap is None:
            rootcap = await self.create_rootcap()
        subdirs = await self.gateway.ls(
            danger_real_capability_string(rootcap), exclude_filenodes=True
        )
        if subdirs is None:
            raise ValueError("Unable to list contents of Tahoe-LAFS rootcap")
        self._basedircap = subdirs.get(self.basedir, {}).get("cap", "")
        if self._basedircap:
            return self._basedircap
        await self.lock.acquire()
        if self._basedircap:
            self.lock.release()
            return self._basedircap
        logging.debug('Creating base ("%s") dircap...', self.basedir)
        try:
            self._basedircap = await self.gateway.mkdir(
                danger_real_capability_string(rootcap), self.basedir
            )
        finally:
            self.lock.release()
        logging.debug('Base ("%s") dircap successfully created', self.basedir)
        return self._basedircap

    async def create_backup_cap(self, name: str, basedircap: str = "") -> str:
        if not basedircap:
            basedircap = await self._get_basedircap()
        await self.lock.acquire()
        try:
            backup_cap = await self.gateway.mkdir(basedircap, name)
        finally:
            self.lock.release()
        self._backup_caps[name] = backup_cap
        return backup_cap

    async def get_backup_cap(self, name: str, basedircap: str = "") -> str:
        backup_cap = self._backup_caps.get(name)
        if backup_cap:
            return backup_cap
        if not basedircap:
            basedircap = await self._get_basedircap()
        ls_output = await self.gateway.ls(basedircap, exclude_filenodes=True)
        if ls_output is None:
            raise ValueError("Failed to list backup contents")
        backup_caps = {}
        for dirname, data in ls_output.items():
            backup_caps[dirname] = data.get("cap", "")
        backup_cap = backup_caps.get(name, "")
        if not backup_cap:
            backup_cap = await self.create_backup_cap(name, basedircap)
            backup_caps[name] = backup_cap
        self._backup_caps = backup_caps
        return backup_cap

    async def add_backup(self, dirname: str, name: str, cap: str) -> None:
        backup_cap = await self.get_backup_cap(dirname)
        await self.lock.acquire()
        try:
            await self.gateway.link(backup_cap, name, cap)
        finally:
            self.lock.release()

    async def get_backup(self, dirname: str, name: str) -> str:
        """
        Retrieve a backup previously added with `add_backup`.

        :param dirname: same meaning as add_backup
        :param name: same meaning as add_backup
        """
        backup_cap = await self.get_backup_cap(dirname)
        ls_output = await self.gateway.ls(backup_cap)
        if ls_output is None:
            raise ValueError("Failed to list backup contents")
        for directory, data in ls_output.items():
            if directory == name:
                return data["cap"]
        raise ValueError(f"Backup not found for {dirname} -> {name}")

    async def get_backups(self, dirname: str) -> Optional[dict]:
        backup_cap = await self.get_backup_cap(dirname)
        ls_output = await self.gateway.ls(backup_cap)
        return ls_output

    async def remove_backup(self, dirname: str, name: str) -> None:
        backup_cap = await self.get_backup_cap(dirname)
        await self.lock.acquire()
        try:
            await self.gateway.unlink(backup_cap, name, missing_ok=True)
        finally:
            self.lock.release()
