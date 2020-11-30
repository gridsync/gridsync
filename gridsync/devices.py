# pylint: disable=unsubscriptable-object
# https://github.com/PyCQA/pylint/issues/3882

import logging
import os
from typing import List, Optional

from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks
from twisted.internet.task import deferLater

from gridsync.util import b58encode


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
    def add_devicecap(
        self, root: Optional[str] = "", name: Optional[str] = ""
    ) -> Deferred:
        if not root:
            root = yield self.get_devicescap()
        if not name:
            name = "device-" + b58encode(os.urandom(8))
        devicecap = yield self.gateway.mkdir(root, name)
        return (name, devicecap)

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
    def link_folders(
        self,
        folders: Optional[List[str]] = None,
        devices: Optional[List[str]] = None,
    ) -> Deferred:
        if not folders:
            folders = list(self.gateway.magic_folders)
        if not folders:
            logging.warning("No folders found to link")
        link_targets = []
        if not devices:
            new = yield self.add_devicecap()
            name, cap = new
            link_targets = [(name, cap)]
        else:
            devicecaps = yield self.get_devicecaps()
            for name, cap in devicecaps:
                for device in devices:
                    if device == name:
                        link_targets.append((name, cap))
        print(link_targets)
        for folder in folders:
            for target in link_targets:
                _, dircap = target
                yield self._do_link(folder, dircap)
        devicecap = yield self.add_devicecap()  # XXX
        return devicecap

    @inlineCallbacks
    def invite_device(self, device: str, folder: str):
        logging.debug("Inviting %s to folder '%s'...", device, folder)
        #code = yield self.gateway.magic_folder_invite(folder, device)
        yield deferLater(reactor, 2, lambda: None)  # XXX
        code = "test+test"
        logging.debug(
            "Sucessfully invited %s to folder '%s'...", device, folder
        )
        return code

    @inlineCallbacks
    def add_new_device(
        self, device: str = "", folders: Optional[List[str]] = None
    ) -> Deferred:
        if not device:
            device = "device-" + b58encode(os.urandom(8))
        if not folders:
            folders = list(self.gateway.magic_folders)
        if not folders:
            logging.warning("No folders found to link")
        print('------------------------------------------------------')
        tasks = []
        for folder in folders:
            tasks.append(self.invite_device(device, folder))
            tasks.append(self.invite_device(device, folder))
        results = yield DeferredList(tasks, consumeErrors=True)
        print("#######################", results)
        for success, result in results:
            print(success, result)
        codes = []
        devicecap = yield self.add_devicecap("", device)
        name, cap = devicecap
        print('!!!!!!!!!!!!!!!!', name, cap)
        return cap

    # @inlineCallbacks
    # def ls(self, cap: str):
    #    results = []
    #    json_data = yield self.gateway.get_json(cap)
    #    if json_data:
    #        for filename, data in json_data[1]["children"].items():
    #            kind = data[0]
    #            metadata = data[1]
    #            mutable = metadata.get("mutable", False)
    #            size = metadata.get("size", 0)
    #            cap = metadata.get("rw_uri", metadata.get("ro_uri", ""))
    #            mtime = metadata["metadata"]["tahoe"].get("linkmotime", 0)
    #            results.append((filename, kind, mutable, size, mtime, cap))
    #    return results
