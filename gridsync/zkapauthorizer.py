# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import logging as log
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import treq
from atomicwrites import atomic_write
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectError

from gridsync.errors import TahoeWebError
from gridsync.types import TreqResponse, TwistedDeferred
from gridsync.voucher import generate_voucher

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class ZKAPAuthorizer:
    def __init__(self, gateway: Tahoe) -> None:
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

    @inlineCallbacks
    def _request(
        self, method: str, path: str, data: Optional[bytes] = None
    ) -> TwistedDeferred[TreqResponse]:
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.request(
            method,
            f"{nodeurl}storage-plugins/privatestorageio-zkapauthz-v1{path}",
            headers={
                "Authorization": f"tahoe-lafs {api_token}",
                "Content-Type": "application/json",
            },
            data=data,
        )
        return resp

    @inlineCallbacks
    def add_voucher(
        self, voucher: Optional[str] = None
    ) -> TwistedDeferred[str]:
        if not voucher:
            voucher = generate_voucher()
        resp = yield self._request(
            "PUT", "/voucher", json.dumps({"voucher": voucher}).encode()
        )
        if resp.code == 200:  # type: ignore
            return voucher
        raise TahoeWebError(f"Error adding voucher: {resp.code}")  # type: ignore

    @inlineCallbacks
    def get_voucher(self, voucher: str) -> TwistedDeferred[Dict]:
        resp = yield self._request("GET", f"/voucher/{voucher}")
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting voucher: {resp.code}")  # type: ignore

    @inlineCallbacks
    def get_vouchers(self) -> TwistedDeferred[List]:
        resp = yield self._request("GET", "/voucher")
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content.get("vouchers")  # type: ignore
        raise TahoeWebError(f"Error getting vouchers: {resp.code}")  # type: ignore

    @inlineCallbacks
    def get_zkaps(
        self, limit: Optional[int] = 0, position: Optional[str] = None
    ) -> TwistedDeferred[bytes]:
        query_params = []
        if limit:
            query_params.append(f"limit={limit}")
        if position:
            query_params.append(f"position={position}")
        if query_params:
            query_string = "?" + "&".join(query_params)
        else:
            query_string = ""
        resp = yield self._request("GET", f"/unblinded-token{query_string}")
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting ZKAPs: {resp.code}")  # type: ignore

    def zkap_payment_url(self, voucher: str) -> str:
        if not self.zkap_payment_url_root:
            return ""
        return "{}?voucher={}&checksum={}".format(
            self.zkap_payment_url_root,
            voucher,
            hashlib.sha256(voucher.encode()).hexdigest(),
        )

    @inlineCallbacks
    def get_zkap_dircap(self) -> TwistedDeferred[str]:
        if not self.gateway.get_rootcap():
            yield self.gateway.create_rootcap()
        if self.zkap_dircap:
            return self.zkap_dircap
        root_json = yield self.gateway.get_json(self.gateway.rootcap)
        try:
            self.zkap_dircap = root_json[1]["children"][".zkaps"][1]["rw_uri"]  # type: ignore
        except KeyError:
            self.zkap_dircap = yield self.gateway.mkdir(
                self.gateway.rootcap, ".zkaps"
            )
        return self.zkap_dircap

    @inlineCallbacks
    def update_zkap_checkpoint(
        self, _: Optional[Any] = None
    ) -> TwistedDeferred[None]:
        if not self.gateway.zkap_auth_required:
            return
        zkaps_dir = os.path.join(self.gateway.nodedir, "private", "zkaps")
        os.makedirs(zkaps_dir, exist_ok=True)

        # The act of updating the checkpoint itself costs at least 1
        # ZKAP, so use the *second* token as the "checkpoint" (on the
        # assumption that the first/next token will be spent imminently)
        zkaps = yield self.get_zkaps(2)
        checkpoint = zkaps.get("unblinded-tokens")[1]  # type: ignore
        checkpoint_path = os.path.join(zkaps_dir, "checkpoint")
        with atomic_write(checkpoint_path, overwrite=True) as f:
            f.write(checkpoint.strip())

        zkap_dircap = yield self.get_zkap_dircap()
        checkpoint_filecap = yield self.gateway.upload(checkpoint_path)
        yield self.gateway.link(zkap_dircap, "checkpoint", checkpoint_filecap)

    @inlineCallbacks
    def backup_zkaps(self, timestamp: str) -> TwistedDeferred[None]:
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
        zkaps["last-redeemed"] = timestamp  # type: ignore

        with atomic_write(temp_path, overwrite=True) as f:  # type: ignore
            f.write(json.dumps(zkaps))

        zkap_dircap = yield self.get_zkap_dircap()
        backup_filecap = yield self.gateway.upload(temp_path)
        yield self.gateway.link(zkap_dircap, "backup.json", backup_filecap)

        yield self.update_zkap_checkpoint()

        shutil.move(temp_path, local_backup_path)

    @inlineCallbacks
    def insert_zkaps(self, zkaps: list) -> TwistedDeferred[Dict]:
        resp = yield self._request(
            "POST",
            "/unblinded-token",
            json.dumps({"unblinded-tokens": zkaps}).encode(),
        )
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error inserting ZKAPs: {resp.code}")  # type: ignore

    @inlineCallbacks
    def _get_content(self, cap: str) -> TwistedDeferred[bytes]:
        yield self.gateway.await_ready()
        resp = yield treq.get(f"{self.gateway.nodeurl}uri/{cap}")
        content = yield treq.content(resp)
        if resp.code == 200:  # type: ignore
            return content
        raise TahoeWebError(content.decode("utf-8"))  # type: ignore

    @inlineCallbacks
    def restore_zkaps(self) -> TwistedDeferred[None]:
        zkap_dircap = yield self.get_zkap_dircap()

        backup = yield self._get_content(zkap_dircap + "/backup.json")  # type: ignore
        backup_decoded = json.loads(backup.decode())  # type: ignore
        tokens = backup_decoded.get("unblinded-tokens")

        checkpoint = yield self._get_content(zkap_dircap + "/checkpoint")  # type: ignore
        checkpoint = checkpoint.decode()  # type: ignore

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
    def get_version(self) -> TwistedDeferred[str]:
        version = ""
        resp = yield self._request("GET", "/version")
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            version = content.get("version", "")  # type: ignore
        return version

    @inlineCallbacks
    def get_bytes(self, cap: str) -> TwistedDeferred[bytes]:
        nodeurl = self.gateway.nodeurl
        if not cap or not nodeurl:
            return b""
        try:
            resp = yield treq.get(f"{nodeurl}uri/{cap}")
        except ConnectError:
            return b""
        if resp.code == 200:  # type: ignore
            content = yield treq.content(resp)
            return content
        raise TahoeWebError(f"Error getting bytes: {resp.code}")  # type: ignore

    @inlineCallbacks
    def get_sizes(self) -> TwistedDeferred[List[Optional[int]]]:
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
    def calculate_price(self, sizes: List[int]) -> TwistedDeferred[Dict]:
        if not self.gateway.nodeurl:
            return {}
        resp = yield self._request(
            "POST",
            "/calculate-price",
            json.dumps({"version": 1, "sizes": sizes}).encode(),
        )
        if resp.code == 200:  # type: ignore
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(
            f"Error calculating price: {resp.code}"  # type: ignore
        )

    @inlineCallbacks
    def get_price(self) -> TwistedDeferred[Dict]:
        sizes = yield self.get_sizes()
        price = yield self.calculate_price(sizes)
        return price
