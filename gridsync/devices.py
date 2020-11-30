# pylint: disable=unsubscriptable-object
# https://github.com/PyCQA/pylint/issues/3882

import logging
from typing import List, Optional

from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks


class DevicesManager:
    def __init__(self, gateway) -> None:
        self.gateway = gateway

        self.devicescap: str = ""

    @inlineCallbacks
    def create_devicescap(self) -> Deferred:
        yield self.gateway.lock.acquire()
        try:
            cap = yield self.gateway.mkdir(
                self.gateway.get_rootcap(), ".devices"
            )
        finally:
            yield self.gateway.lock.release()
        return cap

    @inlineCallbacks
    def get_devicescap(self) -> Deferred:
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
    def add_devicecap(self, name: str, root: Optional[str] = "") -> Deferred:
        if not root:
            root = yield self.get_devicescap()
        devicecap = yield self.gateway.mkdir(root, name)
        return devicecap

    @inlineCallbacks
    def get_devicecaps(self, root: Optional[str] = "") -> Deferred:
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
    def _do_invite(self, device: str, folder: str) -> Deferred:
        code = yield self.gateway.magic_folder_invite(folder, device)
        return folder, code

    @inlineCallbacks
    def add_new_device(self, device: str, folders: List[str]) -> Deferred:
        if not folders:
            logging.warning("No folders found to link")

        devicecap = yield self.add_devicecap(device)

        tasks = []
        for folder in folders:
            tasks.append(self._do_invite(device, folder))
        results = yield DeferredList(tasks, consumeErrors=True)

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
        yield DeferredList(tasks, consumeErrors=True)
        return devicecap

    @inlineCallbacks
    def add_new_folder(self, folder: str, devices: List[str]) -> Deferred:
        pass
