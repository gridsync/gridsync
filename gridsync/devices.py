import logging
import os
from typing import List, Optional

from twisted.internet.defer import Deferred, inlineCallbacks

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
    def link_folders(
        self,
        folders: Optional[List[str]] = None,
        devices: Optional[List[str]] = None,
    ) -> Deferred:
        # TODO:
        #  - Get folders
        #  - Get devicecaps
        #  - Link folders into devicecap(s)
        devicecap = yield self.add_devicecap()
        # yield self.get_devicecaps()
        return devicecap

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
