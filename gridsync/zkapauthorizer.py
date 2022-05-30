# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import treq
from twisted.internet.defer import inlineCallbacks

from gridsync.errors import TahoeWebError
from gridsync.types import TreqResponse, TwistedDeferred
from gridsync.voucher import generate_voucher

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import

PLUGIN_NAME = "privatestorageio-zkapauthz-v2"


class ZKAPAuthorizer:
    def __init__(self, gateway: Tahoe) -> None:
        self.gateway = gateway

        self.zkap_unit_name: str = "MB-month"
        self.zkap_unit_multiplier: int = 1
        self.zkap_payment_url_root: str = ""
        self.zkap_dircap: str = ""
        # Default batch-size from zkapauthorizer.resource.NUM_TOKENS
        self.zkap_batch_size: int = 2**15

        # XXX/TODO: Move this later?
        gateway.monitor.zkaps_redeemed.connect(lambda _: self.backup_zkaps())

    @inlineCallbacks
    def _request(
        self, method: str, path: str, data: Optional[bytes] = None
    ) -> TwistedDeferred[TreqResponse]:
        nodeurl = self.gateway.nodeurl
        api_token = self.gateway.api_token
        resp = yield treq.request(
            method,
            f"{nodeurl}storage-plugins/{PLUGIN_NAME}{path}",
            headers={
                "Authorization": f"tahoe-lafs {api_token}",
                "Content-Type": "application/json",
            },
            data=data,
        )
        return resp

    @inlineCallbacks
    def get_version(self) -> TwistedDeferred[str]:
        version = ""
        resp = yield self._request("GET", "/version")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            version = content.get("version", "")
        return version

    @inlineCallbacks
    def _get_content(self, cap: str) -> TwistedDeferred[bytes]:
        resp = yield treq.get(f"{self.gateway.nodeurl}uri/{cap}")
        if resp.code == 200:
            content = yield treq.content(resp)
            return content
        raise TahoeWebError(f"Error getting cap content: {resp.code}")

    @inlineCallbacks
    def get_sizes(self) -> TwistedDeferred[List[Optional[int]]]:
        sizes: list = []
        rootcap = self.gateway.get_rootcap()
        rootcap_bytes = yield self._get_content(f"{rootcap}/?t=json")
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
                dircap_bytes = yield self._get_content(f"{dircap}/?t=json")
                sizes.append(len(dircap_bytes))
                dircap_data = json.loads(dircap_bytes.decode("utf-8"))
                for data in dircap_data[1]["children"].values():
                    size = data[1].get("size", 0)
                    if size:
                        sizes.append(size)
        mf_sizes = yield self.gateway.magic_folder.get_all_object_sizes()
        sizes.extend(mf_sizes)
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
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error calculating price: {resp.code}")

    @inlineCallbacks
    def get_price(self) -> TwistedDeferred[Dict]:
        sizes = yield self.get_sizes()
        price = yield self.calculate_price(sizes)
        return price

    @inlineCallbacks
    def add_voucher(
        self, voucher: Optional[str] = None
    ) -> TwistedDeferred[str]:
        if not voucher:
            voucher = generate_voucher()
        resp = yield self._request(
            "PUT", "/voucher", json.dumps({"voucher": voucher}).encode()
        )
        if resp.code == 200:
            return voucher
        content = yield resp.content()
        raise TahoeWebError(f"Error adding voucher: {resp.code}: {content}")

    @inlineCallbacks
    def get_voucher(self, voucher: str) -> TwistedDeferred[Dict]:
        resp = yield self._request("GET", f"/voucher/{voucher}")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting voucher: {resp.code}")

    @inlineCallbacks
    def get_vouchers(self) -> TwistedDeferred[List]:
        resp = yield self._request("GET", "/voucher")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content.get("vouchers")
        raise TahoeWebError(f"Error getting vouchers: {resp.code}")

    def zkap_payment_url(self, voucher: str) -> str:
        if not self.zkap_payment_url_root:
            return ""
        return "{}?voucher={}&checksum={}".format(
            self.zkap_payment_url_root,
            voucher,
            hashlib.sha256(voucher.encode()).hexdigest(),
        )

    @inlineCallbacks
    def get_total_zkaps(self) -> TwistedDeferred[int]:
        """
        Uses the /lease-maintenance endpoint to ask ZKAPAuthorizer how
        many tokens it knows about.

        :returns: the total number of ZKAPs we have (spend and unspent
            together)
        """
        resp = yield self._request("GET", "/lease-maintenance")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content.get("total", 0)
        raise TahoeWebError(f"Error getting ZKAPs: {resp.code}")

    @inlineCallbacks
    def get_lease_maintenance_spending(
        self,
    ) -> TwistedDeferred[Union[None, int]]:
        """
        Uses the /lease-maintenance endpoint to ask ZKAPAuthorizer how
        much we've spent on lease-maintenance

        :returns: ???
        """
        resp = yield self._request("GET", "/lease-maintenance")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content.get("spending", None)
        raise TahoeWebError(f"Error getting ZKAPs: {resp.code}")

    @inlineCallbacks
    def _setup_replication(self) -> TwistedDeferred[str]:
        """
        Configure replication of ZKAPAuthorizer state via the /replicate
        endpoint. This returns a Tahoe-LAFS read-only directory
        capability that needs to be returned to the ZKAPAuthorizer to
        complete a later recovery.

        :returns: a capability of type `URI:DIR2-RO:`
        """
        resp = yield self._request("POST", "/replicate")
        if resp.code == 201:
            content = yield treq.json_content(resp)
            return content.get("recovery-capability")
        raise TahoeWebError(f"Error configuring replication: {resp.code}")

    @inlineCallbacks
    def _recover(self, dircap: str) -> TwistedDeferred[None]:
        """
        Call the ZKAPAuthorizer /recover endpoint and await its
        results. The endpoint only returns after the recovery is
        complete.

        :raises TahoeWebError" if anything other than 202 ACCEPTED is
            the result of the operation.
        """
        resp = yield self._request(
            "POST",
            "/recover",
            json.dumps({"recovery-capability": dircap}).encode(),
        )
        if resp.code != 202:
            raise TahoeWebError(f"Error starting recovery: {resp.code}")

    @inlineCallbacks
    def get_recovery_status(self) -> TwistedDeferred[dict]:
        resp = yield self._request("GET", "/recover")
        if resp.code == 200:
            content = yield treq.json_content(resp)
            return content
        raise TahoeWebError(f"Error getting recovery status: {resp.code}")

    @inlineCallbacks
    def await_recovery_succeeded(self) -> TwistedDeferred[None]:
        from twisted.internet import reactor
        from twisted.internet.task import deferLater

        while True:
            status = yield self.get_recovery_status()
            stage = status.get("stage", "")
            failure_reason = status.get("failure-reason", "")
            print("###", stage, failure_reason)  # XXX
            if failure_reason:
                raise Exception(failure_reason)  # XXX
            # https://github.com/PrivateStorageio/ZKAPAuthorizer/blob/
            # cb0443d8011e1485b73f00637e972e06cc3d2757/src/_zkapauthorizer/
            # recover.py#L52-L57=
            if stage == "succeeded":
                return
            yield deferLater(reactor, 1, lambda: None)  # type: ignore

    @inlineCallbacks
    def backup_zkaps(self) -> TwistedDeferred[None]:
        """
        Set up ZKAPAuthorizer state replication and link its read-only
        directory cap under the ``.zkapauthorizer`` backup under name
        ``recovery-capability``.
        """
        cap = yield self._setup_replication()
        yield self.gateway.rootcap_manager.add_backup(
            ".zkapauthorizer", "recovery-capability", cap
        )

    @inlineCallbacks
    def restore_zkaps(self) -> TwistedDeferred[None]:
        """
        Attempt to restore ZKAP state from a previously saved
        replica. Uses the ``recovery-capability`` from the
        ``.zkapauthorizer`` backup, which should be there from a
        previous call to ``backup_zkaps``.
        """
        cap = yield self.gateway.rootcap_manager.get_backup(
            ".zkapauthorizer", "recovery-capability"
        )
        yield self._recover(cap)
        yield self.await_recovery_succeeded()
