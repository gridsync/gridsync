# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Callable, Optional

import treq
from autobahn.twisted.websocket import create_client_agent
from twisted.internet.defer import Deferred, inlineCallbacks

from gridsync.errors import TahoeWebError
from gridsync.types_ import TwistedDeferred
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
        self._recovery_capability: str = ""

        # XXX/TODO: Move this later?
        gateway.monitor.zkaps_redeemed.connect(lambda _: self.backup_zkaps())

    def converted_batch_size(self, value: Optional[int] = None) -> float:
        """
        Compute an effective batch size for the given raw batch size which
        reflects things like Tahoe-LAFS erasure encoding overhead.

        The effective size more directly represents how much user-facing data
        you might expect to be able to store.
        """
        if value is None:
            value = self.zkap_batch_size
        if self.zkap_unit_multiplier == 1:
            return value
        if value < 10:
            return round(value * self.zkap_unit_multiplier, 3)
        return round(value * self.zkap_unit_multiplier, 2)

    @inlineCallbacks
    def _request(
        self, method: str, path: str, data: Optional[bytes] = None
    ) -> TwistedDeferred[tuple[int, str]]:
        resp = yield treq.request(
            method,
            f"{self.gateway.nodeurl}storage-plugins/{PLUGIN_NAME}{path}",
            headers={
                "Authorization": f"tahoe-lafs {self.gateway.api_token}",
                "Content-Type": "application/json",
            },
            data=data,
        )
        content = yield treq.content(resp)
        return (resp.code, content.decode("utf-8").strip())

    @inlineCallbacks
    def get_version(self) -> TwistedDeferred[str]:
        code, body = yield self._request("GET", "/version")
        if code == 200:
            return json.loads(body).get("version", "")
        raise TahoeWebError(
            f"Error ({code}) getting ZKAPAuthorizer version: {body}"
        )

    @inlineCallbacks
    def _get_content(self, cap: str) -> TwistedDeferred[bytes]:
        resp = yield treq.get(f"{self.gateway.nodeurl}uri/{cap}")
        if resp.code == 200:
            content = yield treq.content(resp)
            return content
        raise TahoeWebError(f"Error getting cap content: {resp.code}")

    @inlineCallbacks
    def get_sizes(self) -> TwistedDeferred[list[Optional[int]]]:
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
        mf_sizes = yield Deferred.fromCoroutine(
            self.gateway.magic_folder.get_all_object_sizes()
        )
        sizes.extend(mf_sizes)
        return sizes

    @inlineCallbacks
    def calculate_price(self, sizes: list[int]) -> TwistedDeferred[dict]:
        if not self.gateway.nodeurl:
            return {}
        code, body = yield self._request(
            "POST",
            "/calculate-price",
            json.dumps({"version": 1, "sizes": sizes}).encode(),
        )
        if code == 200:
            return json.loads(body)
        raise TahoeWebError(f"Error ({code}) calculating price: {body}")

    @inlineCallbacks
    def get_price(self) -> TwistedDeferred[dict]:
        sizes = yield self.get_sizes()
        price = yield self.calculate_price(sizes)
        return price

    @inlineCallbacks
    def add_voucher(
        self, voucher: Optional[str] = None
    ) -> TwistedDeferred[str]:
        if not voucher:
            voucher = generate_voucher()
        code, body = yield self._request(
            "PUT", "/voucher", json.dumps({"voucher": voucher}).encode()
        )
        if code == 200:
            return voucher
        raise TahoeWebError(f"Error ({code}) adding voucher: {body}")

    @inlineCallbacks
    def get_voucher(self, voucher: str) -> TwistedDeferred[dict]:
        code, body = yield self._request("GET", f"/voucher/{voucher}")
        if code == 200:
            return json.loads(body)
        raise TahoeWebError(f"Error ({code}) getting voucher: {body}")

    @inlineCallbacks
    def get_vouchers(self) -> TwistedDeferred[list]:
        code, body = yield self._request("GET", "/voucher")
        if code == 200:
            return json.loads(body).get("vouchers")
        raise TahoeWebError(f"Error ({code}) getting vouchers: {body}")

    def zkap_payment_url(self, voucher: str) -> str:
        if not self.zkap_payment_url_root:
            return ""
        return "{}?voucher={}&checksum={}".format(
            self.zkap_payment_url_root,
            voucher,
            hashlib.sha256(voucher.encode()).hexdigest(),
        )

    @inlineCallbacks
    def get_lease_maintenance(self) -> TwistedDeferred[dict]:
        """
        Uses the /lease-maintenance endpoint to ask ZKAPAuthorizer for
        lease-maintenance-related information

        :returns: a dict containing information about lease-maintenance
        """
        code, body = yield self._request("GET", "/lease-maintenance")
        if code == 200:
            return json.loads(body)
        raise TahoeWebError(
            f"Error ({code}) getting lease-maintenance information: {body}"
        )

    @inlineCallbacks
    def replicate(self) -> TwistedDeferred[str]:
        """
        Configure replication of ZKAPAuthorizer state via the /replicate
        endpoint. This returns a Tahoe-LAFS read-only directory
        capability that needs to be returned to the ZKAPAuthorizer to
        complete a later recovery.

        :returns: a capability of type `URI:DIR2-RO:`
        """
        code, body = yield self._request("POST", "/replicate")
        if code in (201, 409):
            return json.loads(body).get("recovery-capability")
        raise TahoeWebError(
            f"Error ({code}) getting recovery capability: {body}"
        )

    @inlineCallbacks
    def recover(
        self, dircap: str, on_status_update: Callable
    ) -> TwistedDeferred[None]:
        """
        Call the ZKAPAuthorizer /recover WebSocket endpoint and await its
        results. The endpoint only returns after the recovery is
        complete.
        """
        uri = f"{self.gateway.nodeurl}storage-plugins/{PLUGIN_NAME}/recover".replace(
            "http", "ws"
        )
        from twisted.internet import reactor

        agent = create_client_agent(reactor)
        proto = yield agent.open(
            uri,
            {
                "headers": {
                    "Authorization": f"tahoe-lafs {self.gateway.api_token}"
                }
            },
        )

        def status_update(raw_data: bytes, is_binary: bool = False) -> None:
            if is_binary:
                return  # XXX Warn?
            data = json.loads(raw_data)
            on_status_update(data["stage"], data["failure-reason"])

        proto.on("message", status_update)

        yield proto.is_open
        yield proto.sendMessage(
            json.dumps({"recovery-capability": dircap}).encode("utf8")
        )
        try:
            yield proto.is_closed
        except Exception as e:
            raise TahoeWebError(f"Error during recovery: {e}") from e

    @inlineCallbacks
    def backup_zkaps(self) -> TwistedDeferred[None]:
        """
        Set up ZKAPAuthorizer state replication and link its read-only
        directory cap under the ``.zkapauthorizer`` backup under name
        ``recovery-capability``.
        """
        try:
            recovery_cap = yield self.replicate()
        except (json.decoder.JSONDecodeError, TahoeWebError):
            recovery_cap = self._recovery_capability
        if recovery_cap and recovery_cap != self._recovery_capability:
            # Cache the recovery capability since the version of
            # ZKAPAuthorizer that is currently on PyPI (v2022.6.28)
            # only gives us the capability one time (for HTTP status
            # 201/"CREATED"). A future version will fix this. See:
            # https://github.com/PrivateStorageio/ZKAPAuthorizer
            # /commit/dce40ecc5779a4c8428d83ed8418fd4b178589f1
            self._recovery_capability = recovery_cap
        try:
            backup_cap = yield Deferred.fromCoroutine(
                self.gateway.rootcap_manager.get_backup(
                    ".zkapauthorizer", "recovery-capability"
                )
            )
        except ValueError:
            backup_cap = ""
        if recovery_cap and recovery_cap != backup_cap:
            yield Deferred.fromCoroutine(
                self.gateway.rootcap_manager.add_backup(
                    ".zkapauthorizer", "recovery-capability", recovery_cap
                )
            )
        else:
            logging.warning(
                "ZKAPAuthorizer replication is already configured."
            )

    @inlineCallbacks
    def get_recovery_capability(
        self, rootcap: Optional[str] = None
    ) -> TwistedDeferred[Optional[str]]:
        """
        Get the ZKAPAuthorizer recovery-capability from RootcapManager.

        If `rootcap` is provided, bypass RootcapManager and instead try
        to get the recovery-capability by traversing the same path from
        the given rootcap.
        """
        if rootcap:
            recovery_cap = yield Deferred.fromCoroutine(
                self.gateway.get_cap(
                    rootcap + f"/{self.gateway.rootcap_manager.basedir}"
                    "/.zkapauthorizer/recovery-capability"
                )
            )
        else:
            try:
                recovery_cap = yield Deferred.fromCoroutine(
                    self.gateway.rootcap_manager.get_backup(
                        ".zkapauthorizer", "recovery-capability"
                    )
                )
            except ValueError:
                return None
        return recovery_cap

    @inlineCallbacks
    def snapshot_exists(self, recovery_cap: str) -> TwistedDeferred[bool]:
        # TODO: Perhaps the ZKAPAuthorizer plugin should provide this?
        """
        Check whether a snapshot has been stored beneath the given
        ZKAPAuthorizer recovery-capability.

        :returns: `True` if a snapshot exists, `False` otherwise.
        """
        ls_output = yield Deferred.fromCoroutine(self.gateway.ls(recovery_cap))
        if ls_output and "snapshot" in ls_output:
            return True
        return False

    @inlineCallbacks
    def restore_zkaps(
        self, on_status_update: Callable, recovery_cap: Optional[str] = None
    ) -> TwistedDeferred[None]:
        """
        Attempt to restore ZKAP state from a previously saved replica.

        If ``recovery_cap`` is not provided, get it from the
        ``.zkapauthorizer`` backup, which should be there from a
        previous call to ``backup_zkaps``.
        """
        if recovery_cap is None:
            recovery_cap = yield Deferred.fromCoroutine(
                self.gateway.rootcap_manager.get_backup(
                    ".zkapauthorizer", "recovery-capability"
                )
            )
        yield self.recover(recovery_cap, on_status_update)
