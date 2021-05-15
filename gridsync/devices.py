from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal as Signal
from twisted.internet.defer import DeferredList, DeferredLock, inlineCallbacks

from gridsync.types import TwistedDeferred

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class DevicesManager(QObject):

    device_linked = Signal(str)  # device name

    def __init__(self, gateway: Tahoe) -> None:
        super().__init__()
        self.gateway = gateway
        self.devicescap: str = ""
        self._devicescap_lock = DeferredLock()

    @inlineCallbacks
    def create_devicescap(self) -> TwistedDeferred[str]:
        yield self.gateway.lock.acquire()
        try:
            cap = yield self.gateway.mkdir(
                self.gateway.get_rootcap(), ".devices"
            )
        finally:
            yield self.gateway.lock.release()
        return cap

    @inlineCallbacks
    def get_devicescap(self) -> TwistedDeferred[str]:
        if self.devicescap:
            return self.devicescap
        rootcap = self.gateway.get_rootcap()
        yield self.gateway.await_ready()
        data = yield self.gateway.get_json(rootcap)
        try:
            self.devicescap = data[1]["children"][".devices"][1]["rw_uri"]
        except (KeyError, TypeError):
            logging.debug("Devicescap not found; creating...")
            self.devicescap = yield self.create_devicescap()
            logging.debug("Devicescap successfully created")
        return self.devicescap

    @inlineCallbacks
    def add_devicecap(
        self, name: str, root: Optional[str] = ""
    ) -> TwistedDeferred[str]:
        if not root:
            root = yield self.get_devicescap()
        yield self._devicescap_lock.acquire()
        try:
            devicecap = yield self.gateway.mkdir(root, name)
        finally:
            yield self._devicescap_lock.release()
        return devicecap

    @inlineCallbacks
    def remove_devicecap(
        self, device_name: str, root: Optional[str] = ""
    ) -> TwistedDeferred[None]:
        logging.debug("Removing device %s...", device_name)
        if not root:
            root = yield self.get_devicescap()
        yield self._devicescap_lock.acquire()
        try:
            yield self.gateway.unlink(root, device_name)
        finally:
            yield self._devicescap_lock.release()
        logging.debug("Removed device %s", device_name)

    @inlineCallbacks
    def get_devicecaps(
        self, root: Optional[str] = ""
    ) -> TwistedDeferred[List]:
        results = []
        if not root:
            root = yield self.get_devicescap()
        json_data = yield self.gateway.get_json(root)
        if json_data:
            for filename, data in json_data[1]["children"].items():
                kind = data[0]
                if kind == "dirnode":
                    metadata = data[1]
                    cap = metadata.get("rw_uri", metadata.get("ro_uri", ""))
                    results.append((filename, cap))
        return results

    @inlineCallbacks
    def get_folders_for_device(
        self, device: str, cap: str
    ) -> TwistedDeferred[Tuple[str, List[str]]]:
        folder_names = []
        folders = yield self.gateway.get_magic_folders(cap)
        if folders:
            for folder_name in folders:
                folder_names.append(folder_name)
        return device, sorted(folder_names)

    @inlineCallbacks
    def get_sharemap(self) -> TwistedDeferred[Dict[str, List[str]]]:
        sharemap = {}
        devicecaps = yield self.get_devicecaps()
        tasks = []
        for name, cap in devicecaps:
            tasks.append(self.get_folders_for_device(name, cap))
        results = yield DeferredList(tasks, consumeErrors=True)  # type: ignore
        for success, result in results:
            if success:
                name, folders = result
                sharemap[name] = folders
        return sharemap

    @inlineCallbacks
    def _do_invite(
        self, device: str, folder: str
    ) -> TwistedDeferred[Tuple[str, str]]:
        code = yield self.gateway.magic_folder_invite(folder, device)
        return folder, code

    @inlineCallbacks
    def add_new_device(
        self, device: str, folders: List[str]
    ) -> TwistedDeferred[str]:
        if not folders:
            logging.warning("No folders found to link")

        devicecap = yield self.add_devicecap(device)

        tasks = []
        for folder in folders:
            tasks.append(self._do_invite(device, folder))
        results = yield DeferredList(tasks, consumeErrors=True)  # type: ignore

        invites = []
        for success, result in results:
            if success:  # TODO: Handle failures? Warn?
                invites.append(result)

        tasks = []
        for folder, code in invites:
            tasks.append(
                self.gateway.link_magic_folder(
                    folder, devicecap, code, grant_admin=False
                )
            )
        yield DeferredList(tasks, consumeErrors=True)  # type: ignore
        return devicecap

    @inlineCallbacks
    def add_new_folder(self, folder: str, devices: List[str]) -> None:
        pass

    @inlineCallbacks
    def remove_devices(self, devices: List[str]) -> TwistedDeferred[None]:
        sharemap = yield self.get_sharemap()

        tasks = []
        for device_name, folders in sharemap.items():
            for folder in folders:
                tasks.append(
                    self.gateway.magic_folder_uninvite(folder, device_name)
                )
        yield DeferredList(tasks, consumeErrors=True)

        tasks = [self.remove_devicecap(device) for device in sharemap.keys()]
        yield DeferredList(tasks, consumeErrors=True)
