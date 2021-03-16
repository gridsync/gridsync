# -*- coding: utf-8 -*-

import errno
import hashlib
import json
import logging as log
import os
import re
import shutil
import signal
import sys
import tempfile
from collections import OrderedDict, defaultdict
from io import BytesIO
from pathlib import Path
from typing import Dict, Generator, List, Optional

import treq
import yaml
from atomicwrites import atomic_write
from twisted.internet.defer import (
    Deferred,
    DeferredList,
    DeferredLock,
    inlineCallbacks,
)
from twisted.internet.error import ConnectError, ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater
from twisted.python.procutils import which

from gridsync import pkgdir
from gridsync import settings as global_settings
from gridsync.config import Config
from gridsync.crypto import trunchash
from gridsync.errors import TahoeCommandError, TahoeError, TahoeWebError
from gridsync.filter import filter_tahoe_log_message
from gridsync.monitor import Monitor
from gridsync.news import NewscapChecker
from gridsync.preferences import get_preference, set_preference
from gridsync.streamedlogs import StreamedLogs
from gridsync.voucher import generate_voucher


class ZKAPAuthorizer:
    def __init__(self, gateway):
        self.gateway = gateway

        self.zkap_name: str = "Zero-Knowledge Access Pass"
        self.zkap_name_abbrev: str = "ZKAP"
        self.zkap_name_plural: str = "Zero-Knowledge Access Passes"
        self.zkap_unit_name: str = "Zero-Knowledge Access Pass"
        self.zkap_unit_name_abbrev: str = "ZKAP"
        self.zkap_unit_name_plural: str = "Zero-Knowledge Access Passes"
        self.zkap_unit_multiplier: int = 1
        self.zkap_payment_url_root: str = ""
        self.zkap_dircap: str = ""
        # Default batch-size from zkapauthorizer.resource.NUM_TOKENS
        self.zkap_batch_size: int = 2 ** 15
        self.settings: dict = {}

        # self.monitor.zkaps_redeemed.connect(self.backup_zkaps)
        # self.monitor.sync_finished.connect(self.update_zkap_checkpoint)

    @inlineCallbacks
    def add_voucher(self, voucher: Optional[str] = None):
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        if not voucher:
            voucher = generate_voucher()
        resp = yield treq.put(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/voucher",
            json.dumps({"voucher": voucher}).encode(),
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        if resp.code == 200:
            return voucher
        raise TahoeWebError(f"Error adding voucher: {resp.code}")

    @inlineCallbacks
    def get_voucher(self, voucher: str):
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.get(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            f"/voucher/{voucher}",
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting voucher: {resp.code}")

    @inlineCallbacks
    def get_vouchers(self):
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.get(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/voucher",
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content.get("vouchers")
        raise TahoeWebError(f"Error getting vouchers: {resp.code}")

    @inlineCallbacks
    def get_zkaps(
        self, limit: Optional[int] = None, position: Optional[str] = None
    ):
        params = {}
        if limit:
            params["limit"] = limit
        if position:
            params["position"] = position  # type: ignore
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.get(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/unblinded-token",
            params=params,
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting ZKAPs: {resp.code}")

    def zkap_payment_url(self, voucher: str) -> str:
        if not self.zkap_payment_url_root:
            return ""
        return "{}?voucher={}&checksum={}".format(
            self.zkap_payment_url_root,
            voucher,
            hashlib.sha256(voucher.encode()).hexdigest(),
        )

    @inlineCallbacks
    def get_zkap_dircap(self):
        if not self.gateway.get_rootcap():
            yield self.gateway.create_rootcap()
        if self.zkap_dircap:
            return self.zkap_dircap
        root_json = yield self.gateway.get_json(self.gateway.rootcap)
        try:
            self.zkap_dircap = root_json[1]["children"][".zkaps"][1]["rw_uri"]
        except KeyError:
            self.zkap_dircap = yield self.gateway.mkdir(
                self.gateway.rootcap, ".zkaps"
            )
        return self.zkap_dircap

    @inlineCallbacks
    def update_zkap_checkpoint(self, _=None):
        if not self.gateway.zkap_auth_required:
            return
        zkaps_dir = os.path.join(self.gateway.nodedir, "private", "zkaps")
        os.makedirs(zkaps_dir, exist_ok=True)

        # The act of updating the checkpoint itself costs at least 1
        # ZKAP, so use the *second* token as the "checkpoint" (on the
        # assumption that the first/next token will be spent imminently)
        zkaps = yield self.get_zkaps(2)
        checkpoint = zkaps.get("unblinded-tokens")[1]
        checkpoint_path = os.path.join(zkaps_dir, "checkpoint")
        with atomic_write(checkpoint_path, overwrite=True) as f:
            f.write(checkpoint.strip())

        zkap_dircap = yield self.get_zkap_dircap()
        checkpoint_filecap = yield self.gateway.upload(checkpoint_path)
        yield self.gateway.link(zkap_dircap, "checkpoint", checkpoint_filecap)

    @inlineCallbacks
    def backup_zkaps(self, timestamp: str):
        zkaps_dir = os.path.join(self.gateway.nodedir, "private", "zkaps")
        os.makedirs(zkaps_dir, exist_ok=True)

        local_backup_filename = timestamp.replace(":", "_") + ".json"
        local_backup_path = os.path.join(zkaps_dir, local_backup_filename)
        if os.path.exists(local_backup_path):
            log.debug("ZKAP backup %s already uploaded", local_backup_filename)
            return
        try:
            with open(os.path.join(zkaps_dir, "last-redeemed")) as f:
                if timestamp == f.read():
                    log.debug(
                        "No ZKAP backup needed for %s; cancelling", timestamp
                    )
                    return
        except OSError:
            pass

        temp_path = os.path.join(zkaps_dir, "backup.json.tmp")

        zkaps = yield self.get_zkaps()
        zkaps["last-redeemed"] = timestamp

        with atomic_write(temp_path, overwrite=True) as f:  # type: ignore
            f.write(json.dumps(zkaps))

        zkap_dircap = yield self.get_zkap_dircap()
        backup_filecap = yield self.gateway.upload(temp_path)
        yield self.gateway.link(zkap_dircap, "backup.json", backup_filecap)

        yield self.update_zkap_checkpoint()

        shutil.move(temp_path, local_backup_path)

    @inlineCallbacks
    def insert_zkaps(self, zkaps: list):
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.post(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/unblinded-token",
            json.dumps({"unblinded-tokens": zkaps}).encode(),
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error inserting ZKAPs: {resp.code}")

    @inlineCallbacks
    def _get_content(self, cap: str):
        yield self.gateway.await_ready()
        resp = yield treq.get(f"{self.gateway.nodeurl}uri/{cap}")
        content = yield treq.content(resp)
        if resp.code == 200:
            return content
        raise TahoeWebError(content.decode("utf-8"))

    @inlineCallbacks
    def restore_zkaps(self):
        zkap_dircap = yield self.get_zkap_dircap()

        backup = yield self._get_content(zkap_dircap + "/backup.json")
        backup_decoded = json.loads(backup.decode())
        tokens = backup_decoded.get("unblinded-tokens")

        checkpoint = yield self._get_content(zkap_dircap + "/checkpoint")
        checkpoint = checkpoint.decode()

        yield self.insert_zkaps(tokens[tokens.index(checkpoint) :])

        zkaps_dir = os.path.join(self.gateway.nodedir, "private", "zkaps")
        os.makedirs(zkaps_dir, exist_ok=True)

        with atomic_write(
            str(Path(zkaps_dir, "last-redeemed")), overwrite=True
        ) as f:
            f.write(str(backup_decoded.get("last-redeemed")))

        with atomic_write(
            str(Path(zkaps_dir, "last-total")), overwrite=True
        ) as f:
            f.write(str(backup_decoded.get("total")))

    @inlineCallbacks
    def get_version(self):
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.get(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/version",
            headers={"Authorization": f"tahoe-lafs {api_token}"},
        )
        version = ""
        if resp.code == 200:
            content = yield treq.json_content(resp)
            version = content.get("version", "")
        return version

    @inlineCallbacks
    def get_bytes(self, cap: str):
        nodeurl = self.gateway.nodeurl
        if not cap or not nodeurl:
            return b""
        try:
            resp = yield treq.get(f"{nodeurl}uri/{cap}")
        except ConnectError:
            return b""
        if resp.code == 200:
            content = yield treq.content(resp)
            return content
        raise TahoeWebError(f"Error getting bytes: {resp.code}")

    @inlineCallbacks
    def get_sizes(self) -> Generator[int, None, List[Optional[int]]]:
        sizes: list = []
        rootcap = self.gateway.get_rootcap()
        rootcap_bytes = yield self.get_bytes(f"{rootcap}/?t=json")
        if not rootcap_bytes:
            return sizes
        sizes.append(len(rootcap_bytes))
        rootcap_data = json.loads(rootcap_bytes.decode("utf-8"))
        if rootcap_data:
            dircaps = []
            for data in rootcap_data[1]["children"].values():
                rw_uri = data[1].get("rw_uri", "")
                if rw_uri:  # Only care about dirs the user can write to
                    dircaps.append(rw_uri)
            for dircap in dircaps:
                dircap_bytes = yield self.get_bytes(f"{dircap}/?t=json")
                sizes.append(len(dircap_bytes))
                dircap_data = json.loads(dircap_bytes.decode("utf-8"))
                for data in dircap_data[1]["children"].values():
                    size = data[1].get("size", 0)
                    if size:
                        sizes.append(size)
        return sizes

    @inlineCallbacks
    def calculate_price(self, sizes: List[int]) -> Generator[int, None, Dict]:
        nodeurl = self.gateway.nodeurl
        if not nodeurl:
            return {}
        api_token = self.gateway.api_token
        resp = yield treq.post(
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1"
            "/calculate-price",
            json.dumps({"version": 1, "sizes": sizes}).encode(),
            headers={
                "Authorization": f"tahoe-lafs {api_token}",
                "Content-Type": "application/json",
            },
        )
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content  # type: ignore
        raise TahoeWebError(
            f"Error calculating price: {resp.code}"  # type: ignore
        )

    @inlineCallbacks
    def get_price(self) -> Generator[int, None, Dict]:
        sizes = yield self.get_sizes()
        price = yield self.calculate_price(sizes)
        return price  # type: ignore
