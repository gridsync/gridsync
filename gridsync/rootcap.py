from __future__ import annotations

import logging
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from atomicwrites import atomic_write
from twisted.internet.defer import DeferredLock
from twisted.internet.threads import deferToThread

from gridsync import APP_NAME, features
from gridsync.errors import UpgradeRequiredError

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

    def __init__(self, gateway: Tahoe, basedir: str = "v1") -> None:
        self.gateway = gateway
        self.basedir = basedir
        self.lock = DeferredLock()
        self._entropy_path = Path(gateway.nodedir, "private", "entropy")
        self._entropy: bytes = b""
        self._rootcap_path = Path(gateway.nodedir, "private", "rootcap")
        self._rootcap: str = ""
        self._basedircap = ""
        self._backup_caps: dict = {}

    def get_entropy(self) -> bytes:
        if self._entropy:
            return self._entropy
        try:
            self._entropy = self._entropy_path.read_bytes()
        except FileNotFoundError:
            return b""
        return self._entropy

    def set_entropy(self, entropy: bytes, overwrite: bool = False) -> None:
        with atomic_write(
            str(self._entropy_path),
            mode="wb",
            overwrite=overwrite,
        ) as f:
            f.write(entropy)
        logging.debug("Entropy saved to file: %s", self._entropy_path)
        self._entropy = entropy

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

    async def create_rootcap(self) -> str:
        logging.debug("Creating rootcap...")
        if self._rootcap_path.exists():
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return self.get_rootcap()
        await self.lock.acquire()
        if features.zkapauthorizer:
            # XXX Tahoe-LAFS 1.20.0 is required to pass a user-supplied
            # key to mkdir but ZKAPAuthorizer currently requires 1.18.
            # Setting these to None creates a rootcap with a random key.
            entropy = None
            rsa_key = None
        else:
            from deterministic_keygen import derive_rsa_key

            entropy = secrets.token_bytes(16)
            try:
                rsa_key = await deferToThread(derive_rsa_key, entropy)
            except Exception as e:  # pylint: disable=broad-except
                logging.error("Failed to derive RSA key from entropy: %s", e)
                self.lock.release()
                raise
        try:
            rootcap = await self.gateway.mkdir(private_key=rsa_key)
        finally:
            self.lock.release()
        if entropy and rsa_key:
            from lafs import derive_mutable_uri

            try:
                expected_rootcap = await deferToThread(
                    derive_mutable_uri, rsa_key, "DIR2"
                )
            except Exception as e:  # pylint: disable=broad-except
                logging.error("Failed to derive rootcap from RSA key: %s", e)
                raise
            if expected_rootcap != rootcap:
                raise ValueError(
                    "Derived rootcap does not match expected value"
                )
        await self.lock.acquire()
        if self._rootcap:
            logging.warning("Rootcap already exists")
            self.lock.release()
            return self._rootcap
        try:
            self.set_rootcap(rootcap)
        except FileExistsError:
            logging.warning(
                "Rootcap file already exists: %s", self._rootcap_path
            )
            return self.get_rootcap()
        finally:
            self.lock.release()
        if entropy is not None:
            self.set_entropy(entropy)
        logging.debug("Rootcap successfully created")
        return self._rootcap

    async def _get_basedircap(self) -> str:
        if self._basedircap:
            return self._basedircap
        rootcap = self.get_rootcap()
        if not rootcap:
            rootcap = await self.create_rootcap()
        subdirs = await self.gateway.ls(rootcap, exclude_filenodes=True)
        if subdirs is None:
            raise ValueError("Failed to list rootcap contents")
        self._basedircap = subdirs.get(self.basedir, {}).get("cap", "")
        if self._basedircap:
            return self._basedircap
        await self.lock.acquire()
        if self._basedircap:
            self.lock.release()
            return self._basedircap
        logging.debug('Creating base ("%s") dircap...', self.basedir)
        try:
            self._basedircap = await self.gateway.mkdir(rootcap, self.basedir)
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

    async def import_rootcap(self, source_dircap: str) -> None:
        src_dirs = await self.gateway.ls(source_dircap, exclude_filenodes=True)
        if src_dirs is None:
            raise ValueError("Failed to list source directory contents")
        if self.basedir not in src_dirs:
            raise UpgradeRequiredError(
                f'The "{self.basedir}" base directory is missing from the '
                "imported rootcap. This probably means that your Recovery Key "
                f"was created with a version of {APP_NAME} that is "
                "incompatible with the current version of the software."
            )
        src_basedircap = src_dirs[self.basedir]["cap"]
        src_backupdirs = await self.gateway.ls(
            src_basedircap, exclude_filenodes=True
        )
        if not src_backupdirs:
            logging.warning("No backups found in imported rootcap")
            return
        for backupdir_name, backupdir_data in src_backupdirs.items():
            dir_contents = await self.gateway.ls(backupdir_data["cap"])
            if not dir_contents:
                logging.warning(
                    'Backup directory "%s" is empty; not restoring',
                    backupdir_name,
                )
                continue
            for name, data in dir_contents.items():
                await self.add_backup(backupdir_name, name, data["cap"])
