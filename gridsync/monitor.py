# -*- coding: utf-8 -*-

import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectError
from twisted.internet.task import LoopingCall

from gridsync.crypto import trunchash
from gridsync.errors import TahoeWebError


class MagicFolderChecker(QObject):

    LOADING = 0
    SYNCING = 1
    SCANNING = 99
    UP_TO_DATE = 2

    sync_started = pyqtSignal()
    sync_finished = pyqtSignal()

    transfer_progress_updated = pyqtSignal(object, object)
    transfer_speed_updated = pyqtSignal(object)
    transfer_seconds_remaining_updated = pyqtSignal(object)

    status_updated = pyqtSignal(int)
    mtime_updated = pyqtSignal(int)
    size_updated = pyqtSignal(object)

    members_updated = pyqtSignal(list)

    file_updated = pyqtSignal(object)
    files_updated = pyqtSignal(list, str, str)

    def __init__(self, gateway, name, remote=False):
        super().__init__()
        self.gateway = gateway
        self.name = name
        self.remote = remote

        self.state = MagicFolderChecker.LOADING
        self.mtime = 0
        self.size = 0

        self.members = []
        self.sizes = []
        self.history = {}
        self.operations = {}

        self.updated_files = []
        self.initial_scan_completed = False

        self.sync_time_started = 0

    def notify_updated_files(self):
        changes = defaultdict(list)
        for item in self.updated_files:
            changes[item["member"]].insert(
                int(item["mtime"]), (item["action"], item["path"])
            )
        self.updated_files = []
        for author, change in changes.items():
            notifications = defaultdict(list)
            for action, path in change:
                if path not in notifications[action]:
                    notifications[action].append(path)
            for action, files in notifications.items():
                logging.debug("%s %s %s", author, action, len(files))
                # Currently, for non-'admin' members, member/author names are
                # random/non-human-meaningful strings, so omit them for now.
                author = ""  # XXX
                self.files_updated.emit(files, action, author)

    def emit_transfer_signals(self, status):
        # This does not take into account erasure coding overhead
        bytes_transferred = 0
        bytes_total = 0
        for task in status:
            if task["queued_at"] >= self.sync_time_started:
                size = task["size"]
                if not size:
                    continue
                if task["status"] in ("queued", "started", "success"):
                    bytes_total += size
                if task["status"] in ("started", "success"):
                    # A (temporary?) workaround for Tahoe-LAFS ticket #2954
                    # whereby 'percent_done' will sometimes exceed 100%
                    # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2954
                    percent_done = min(100, task["percent_done"])
                    bytes_transferred += size * percent_done / 100
        if bytes_transferred and bytes_total:
            self.transfer_progress_updated.emit(bytes_transferred, bytes_total)
            duration = time.time() - self.sync_time_started
            speed = bytes_transferred / duration
            self.transfer_speed_updated.emit(speed)
            bytes_remaining = bytes_total - bytes_transferred
            seconds_remaining = bytes_remaining / speed
            self.transfer_seconds_remaining_updated.emit(seconds_remaining)
            logging.debug(
                "%s: %s / %s (%s%%); %s seconds remaining",
                self.name,
                bytes_transferred,
                bytes_total,
                int(bytes_transferred / bytes_total * 100),
                seconds_remaining,
            )

    def parse_status(self, status_data):
        state = MagicFolderChecker.LOADING
        kind = ""
        filepath = ""
        failures = []
        if status_data is not None:
            for task in status_data:
                status = task["status"]
                path = task["path"]
                queued_at = task["queued_at"]
                if status in ("queued", "started"):
                    if not self.sync_time_started:
                        self.sync_time_started = queued_at
                    elif queued_at < self.sync_time_started:
                        self.sync_time_started = queued_at
                    if not path.endswith("/"):
                        state = MagicFolderChecker.SYNCING
                        kind = task["kind"]
                        filepath = path
                elif status == "failure":
                    failures.append(task)
                self.operations["{}@{}".format(path, queued_at)] = task
            if state == MagicFolderChecker.LOADING:
                if (
                    self.gateway.monitor.grid_checker.is_connected  # XXX
                    and self.initial_scan_completed
                ):
                    state = MagicFolderChecker.UP_TO_DATE
                    self.sync_time_started = 0
        return state, kind, filepath, failures

    def process_status(self, status):
        remote_scan_needed = False
        state, kind, filepath, _ = self.parse_status(status)
        if state == MagicFolderChecker.SYNCING:
            if self.state != MagicFolderChecker.SYNCING:  # Sync just started
                logging.debug("Sync started (%s)", self.name)
                self.sync_started.emit()
            elif self.state == MagicFolderChecker.SYNCING:
                # Sync started earlier; still going
                logging.debug(
                    'Sync in progress (%sing "%s" in "%s")...',
                    kind,
                    trunchash(filepath),
                    self.name,
                )
                # TODO: Emit uploading/downloading signal?
            self.emit_transfer_signals(self.operations.values())
            remote_scan_needed = True
        elif state == MagicFolderChecker.UP_TO_DATE:
            if self.state == MagicFolderChecker.SYNCING:  # Sync just finished
                logging.debug(
                    "Sync complete (%s); doing final scan...", self.name
                )
                remote_scan_needed = True
                state = MagicFolderChecker.SCANNING
            elif self.state == MagicFolderChecker.SCANNING:
                # Final scan just finished
                logging.debug("Final scan complete (%s)", self.name)
                self.sync_finished.emit()
                self.notify_updated_files()
                self.operations = {}
        if state != self.state:
            self.status_updated.emit(state)
        self.state = state
        # TODO: Notify failures/conflicts
        return remote_scan_needed

    def compare_states(self, current, previous):
        for mtime, data in current.items():
            if mtime not in previous:
                if data["deleted"]:
                    data["action"] = "deleted"
                else:
                    path = data["path"]
                    prev_entry = None
                    for prev_data in previous.values():
                        if prev_data["path"] == path:
                            prev_entry = prev_data
                    if prev_entry:
                        if prev_entry["deleted"]:
                            data["action"] = "restored"
                        else:
                            data["action"] = "updated"
                    elif path.endswith("/"):
                        data["action"] = "created"
                    else:
                        data["action"] = "added"
                self.file_updated.emit(data)
                self.updated_files.append(data)

    @inlineCallbacks
    def do_remote_scan(self, members=None):
        members, size, t, history = yield self.gateway.get_magic_folder_state(
            self.name, members
        )
        self.sizes = [data.get("size", 0) for data in history.values()]
        if members:
            members = sorted(members)
            if members != self.members:
                self.members = members
                self.members_updated.emit(members)
            self.size_updated.emit(size)
            self.size = size
            self.mtime_updated.emit(t)
            self.compare_states(history, self.history)
            self.history = history
            if not self.initial_scan_completed:
                self.updated_files = []  # Skip notifications
                self.initial_scan_completed = True

    @inlineCallbacks
    def do_check(self):
        status = yield self.gateway.get_magic_folder_status(self.name)
        scan_needed = self.process_status(status)
        if scan_needed or not self.initial_scan_completed:
            yield self.do_remote_scan()


class GridChecker(QObject):

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self.num_connected = 0
        self.num_known = 0
        self.num_happy = 0
        self.is_connected = False
        self.available_space = 0

    @inlineCallbacks
    def do_check(self):
        results = yield self.gateway.get_grid_status()
        if results:
            num_connected, num_known, available_space = results
        else:
            num_connected = 0
            num_known = 0
            available_space = 0
        if available_space != self.available_space:
            self.available_space = available_space
            self.space_updated.emit(available_space)
        num_happy = self.gateway.shares_happy
        if not num_happy:
            num_happy = 0
        if num_connected != self.num_connected or num_known != self.num_known:
            self.nodes_updated.emit(num_connected, num_known)
            if num_happy and num_connected >= num_happy:
                if not self.is_connected:
                    self.is_connected = True
                    self.connected.emit()
            elif num_happy and num_connected < num_happy:
                if self.is_connected:
                    self.is_connected = False
                    self.disconnected.emit()
            self.num_connected = num_connected
            self.num_known = num_known
            self.num_happy = num_happy


class ZKAPChecker(QObject):

    zkaps_updated = pyqtSignal(int, int)  # used, remaining
    zkaps_redeemed = pyqtSignal(str)  # timestamp
    zkaps_renewal_cost_updated = pyqtSignal(int)
    days_remaining_updated = pyqtSignal(int)
    unpaid_vouchers_updated = pyqtSignal(list)
    low_zkaps_warning = pyqtSignal()

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self._time_started: int = 0
        self._low_zkaps_warning_shown: bool = False

        self.zkaps_remaining: int = 0
        self.zkaps_total: int = 0
        self.zkaps_last_redeemed: str = "0"
        self.zkaps_renewal_cost: int = 0
        self.days_remaining: int = 0
        self.unpaid_vouchers: list = []

    def consumption_rate(self):
        zkaps_spent = self.zkaps_total - self.zkaps_remaining
        last_redeemed = datetime.fromisoformat(self.zkaps_last_redeemed)
        now = datetime.now()
        seconds = datetime.timestamp(now) - datetime.timestamp(last_redeemed)
        consumption_rate = zkaps_spent / seconds
        return consumption_rate

    def _parse_vouchers(  # noqa: max-complexity
        self, vouchers: List[dict]
    ) -> int:
        total = 0
        unpaid_vouchers = self.unpaid_vouchers.copy()
        zkaps_last_redeemed = self.zkaps_last_redeemed
        for voucher in vouchers:
            state = voucher.get("state")
            if not state:
                continue
            name = state.get("name")
            number = voucher.get("number")
            if name == "unpaid":
                if number and number not in unpaid_vouchers:
                    # XXX There is no reliable way of knowing whether the user
                    # intends to pay for an older voucher -- i.e., one that
                    # was created before the before the application started --
                    # so ignore those older vouchers for now and only monitor
                    # those vouchers that were created during *this* run.
                    created = voucher.get("created")
                    if not created:
                        continue
                    time_created = datetime.timestamp(
                        datetime.fromisoformat(created)
                    )
                    if time_created > self._time_started:
                        unpaid_vouchers.append(number)
            elif name == "redeeming":
                total += state.get("expected-tokens", 0)
            elif name == "redeemed":
                if number and number in unpaid_vouchers:
                    unpaid_vouchers.remove(number)
                total += state.get("token-count")
                finished = state.get("finished")
                if finished > zkaps_last_redeemed:
                    zkaps_last_redeemed = finished
        if unpaid_vouchers != self.unpaid_vouchers:
            self.unpaid_vouchers = unpaid_vouchers
            self.unpaid_vouchers_updated.emit(self.unpaid_vouchers)
        if zkaps_last_redeemed != self.zkaps_last_redeemed:
            self.zkaps_last_redeemed = zkaps_last_redeemed
            self.zkaps_redeemed.emit(self.zkaps_last_redeemed)
        return total

    def _maybe_emit_low_zkaps_warning(self):
        if self.zkaps_total and not self._low_zkaps_warning_shown:
            pct_used = 1 - (self.zkaps_remaining / self.zkaps_total)
            if pct_used >= 0.9 or self.days_remaining <= 60:
                self.low_zkaps_warning.emit()
                self._low_zkaps_warning_shown = True

    def _maybe_load_last_redeemed(self) -> None:
        try:
            with open(
                Path(self.gateway.nodedir, "private", "zkaps", "last-redeemed")
            ) as f:
                last_redeemed = f.read()
        except FileNotFoundError:
            return
        self.zkaps_last_redeemed = last_redeemed
        self.zkaps_redeemed.emit(last_redeemed)

    def _maybe_load_last_total(self) -> int:
        try:
            with open(
                Path(self.gateway.nodedir, "private", "zkaps", "last-total")
            ) as f:
                return int(f.read())
        except FileNotFoundError:
            return 0

    def emit_zkaps_updated(self, remaining, total):
        used = total - remaining
        batch_size = self.gateway.zkap_batch_size
        if batch_size:
            batches_consumed = used // batch_size
            tokens_to_trim = batches_consumed * batch_size
            used = used - tokens_to_trim
            total_trimmed = total - tokens_to_trim
            remaining = total_trimmed - used
        else:
            batches_consumed = 0
            tokens_to_trim = 0
            total_trimmed = total
        self.zkaps_updated.emit(used, remaining)
        logging.debug(
            "ZKAPs updated: used: %i, remaining: %i; cumulative total: %i, "
            "trimmed total: %i (batch size: %i, batches consumed: %i; "
            "tokens deducted: %i)",
            used,
            remaining,
            total,
            total_trimmed,
            batch_size,
            batches_consumed,
            tokens_to_trim,
        )

    @inlineCallbacks  # noqa: max-complexity
    def do_check(self):  # noqa: max-complexity
        if not self._time_started:
            self._time_started = time.time()
        if (
            self.gateway.zkap_auth_required is not True
            or not self.gateway.nodeurl
        ):
            return
        try:
            vouchers = yield self.gateway.get_vouchers()
        except (ConnectError, TahoeWebError):
            return  # XXX
        if not vouchers:
            if self.zkaps_last_redeemed == "0":
                self._maybe_load_last_redeemed()
            else:
                self.emit_zkaps_updated(self.zkaps_remaining, self.zkaps_total)
        total = self._parse_vouchers(vouchers)
        try:
            zkaps = yield self.gateway.get_zkaps(limit=1)
        except (ConnectError, TahoeWebError):
            return  # XXX
        remaining = zkaps.get("total")
        if remaining and not total:
            total = self._maybe_load_last_total()
        if not total or remaining > total:
            # When redeeming tokens in batches, ZKAPs become available
            # during the "redeeming" state but the *total* number is
            # not shown until the "redeemed" state. To prevent the
            # appearance of negative ZKAP balances during this time,
            # temporarily consider the current number of remaining
            # ZKAPs to be the total. For more context, see:
            # https://github.com/PrivateStorageio/ZKAPAuthorizer/issues/124
            total = remaining
        if remaining != self.zkaps_remaining or total != self.zkaps_total:
            self.zkaps_remaining = remaining
            self.zkaps_total = total
            self.emit_zkaps_updated(remaining, total)
        elif not remaining or not total:
            self.emit_zkaps_updated(remaining, total)
        spending = zkaps.get("lease-maintenance-spending")
        if spending:
            count = spending.get("count")
        else:
            # If a lease maintenance crawl hasn't yet happened, we can assume
            # that the cost to renew (in the first crawl) will be equivalent
            # to the number of ZKAPs already used/consumed/spent.
            count = self.zkaps_total - self.zkaps_remaining
        if count and count != self.zkaps_renewal_cost:
            self.zkaps_renewal_cost_updated.emit(count)
            self.zkaps_renewal_cost = count

        # XXX/FIXME: This assumes that leases will be renewed every 27 days.
        daily_cost = self.zkaps_renewal_cost / 27
        try:
            days_remaining = int(self.zkaps_remaining / daily_cost)
        except ZeroDivisionError:
            return
        if days_remaining != self.days_remaining:
            self.days_remaining = days_remaining
            self.days_remaining_updated.emit(days_remaining)
        self._maybe_emit_low_zkaps_warning()


class Monitor(QObject):
    """

    :ivar bool _started: Whether or not ``start`` has already been called.
    """

    _started = False

    connected = pyqtSignal()
    disconnected = pyqtSignal()
    nodes_updated = pyqtSignal(int, int)
    space_updated = pyqtSignal(object)

    remote_folder_added = pyqtSignal(str, str)

    sync_started = pyqtSignal(str)
    sync_finished = pyqtSignal(str)

    transfer_progress_updated = pyqtSignal(str, object, object)
    transfer_speed_updated = pyqtSignal(str, object)
    transfer_seconds_remaining_updated = pyqtSignal(str, object)

    status_updated = pyqtSignal(str, int)
    mtime_updated = pyqtSignal(str, int)
    size_updated = pyqtSignal(str, object)

    members_updated = pyqtSignal(str, list)

    file_updated = pyqtSignal(str, object)
    files_updated = pyqtSignal(str, list, str, str)

    total_sync_state_updated = pyqtSignal(int)
    total_folders_size_updated = pyqtSignal(object)  # object avoids overflows

    check_finished = pyqtSignal()

    zkaps_updated = pyqtSignal(int, int)
    zkaps_redeemed = pyqtSignal(str)
    zkaps_renewal_cost_updated = pyqtSignal(int)
    zkaps_price_updated = pyqtSignal(int)
    days_remaining_updated = pyqtSignal(int)
    unpaid_vouchers_updated = pyqtSignal(list)
    low_zkaps_warning = pyqtSignal()

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self.timer = LoopingCall(self.do_checks)
        self.total_folders_size: int = 0
        self.price: dict = {}

        self.grid_checker = GridChecker(self.gateway)
        self.grid_checker.connected.connect(self.connected.emit)
        self.grid_checker.connected.connect(self.scan_rootcap)  # XXX
        self.grid_checker.disconnected.connect(self.disconnected.emit)
        self.grid_checker.nodes_updated.connect(self.nodes_updated.emit)
        self.grid_checker.space_updated.connect(self.space_updated.emit)

        self.zkap_checker = ZKAPChecker(self.gateway)
        self.zkap_checker.zkaps_updated.connect(self.zkaps_updated.emit)
        self.zkap_checker.zkaps_redeemed.connect(self.zkaps_redeemed.emit)
        self.zkap_checker.zkaps_renewal_cost_updated.connect(
            self.zkaps_renewal_cost_updated.emit
        )
        self.zkap_checker.days_remaining_updated.connect(
            self.days_remaining_updated.emit
        )
        self.zkap_checker.unpaid_vouchers_updated.connect(
            self.unpaid_vouchers_updated.emit
        )
        self.zkap_checker.low_zkaps_warning.connect(
            self.low_zkaps_warning.emit
        )

        self.magic_folder_checkers = {}
        self.total_sync_state = 0

    def add_magic_folder_checker(self, name, remote=False):
        mfc = MagicFolderChecker(self.gateway, name, remote)

        mfc.sync_started.connect(lambda: self.sync_started.emit(name))
        mfc.sync_finished.connect(lambda: self.sync_finished.emit(name))

        mfc.transfer_progress_updated.connect(
            lambda x, y: self.transfer_progress_updated.emit(name, x, y)
        )
        mfc.transfer_speed_updated.connect(
            lambda x: self.transfer_speed_updated.emit(name, x)
        )
        mfc.transfer_seconds_remaining_updated.connect(
            lambda x: self.transfer_seconds_remaining_updated.emit(name, x)
        )

        mfc.status_updated.connect(lambda x: self.status_updated.emit(name, x))
        mfc.mtime_updated.connect(lambda x: self.mtime_updated.emit(name, x))
        mfc.size_updated.connect(lambda x: self.size_updated.emit(name, x))

        mfc.members_updated.connect(
            lambda x: self.members_updated.emit(name, x)
        )

        mfc.file_updated.connect(lambda x: self.file_updated.emit(name, x))
        mfc.files_updated.connect(
            lambda x, y, z: self.files_updated.emit(name, x, y, z)
        )

        self.magic_folder_checkers[name] = mfc

    @inlineCallbacks
    def scan_rootcap(self, overlay_file=None):
        logging.debug("Scanning %s rootcap...", self.gateway.name)
        yield self.gateway.await_ready()
        folders = yield self.gateway.get_magic_folders_from_rootcap()
        if not folders:
            return
        for name, caps in folders.items():
            if name not in self.gateway.magic_folders.keys():
                logging.debug(
                    "Found new folder '%s' in rootcap; adding...", name
                )
                self.add_magic_folder_checker(name, remote=True)
                self.remote_folder_added.emit(name, overlay_file)
                c = yield self.gateway.get_json(caps["collective_dircap"])
                members = yield self.gateway.get_magic_folder_members(name, c)
                yield self.magic_folder_checkers[name].do_remote_scan(members)

    @inlineCallbacks
    def do_checks(self):
        yield self.zkap_checker.do_check()
        yield self.grid_checker.do_check()
        for folder in list(self.gateway.magic_folders.keys()):
            if folder not in self.magic_folder_checkers:
                self.add_magic_folder_checker(folder)
            elif self.magic_folder_checkers[folder].remote:
                self.magic_folder_checkers[folder].remote = False
        states = set()
        sizes = []
        total_size = 0
        for magic_folder_checker in list(self.magic_folder_checkers.values()):
            if not magic_folder_checker.remote:
                yield magic_folder_checker.do_check()
                states.add(magic_folder_checker.state)
            sizes += magic_folder_checker.sizes
            total_size += magic_folder_checker.size
        if (
            MagicFolderChecker.SYNCING in states
            or MagicFolderChecker.SCANNING in states
        ):
            # At least one folder is syncing
            state = MagicFolderChecker.SYNCING
        elif len(states) == 1 and MagicFolderChecker.UP_TO_DATE in states:
            # All folders are up to date
            state = MagicFolderChecker.UP_TO_DATE
        else:
            state = MagicFolderChecker.LOADING
        if state != self.total_sync_state:
            self.total_sync_state = state
            self.total_sync_state_updated.emit(state)
        if total_size != self.total_folders_size:
            self.total_folders_size = total_size
            self.total_folders_size_updated.emit(total_size)
            price = yield self.gateway.get_price()
            self.zkaps_price_updated.emit(price.get("price", 0))
        self.check_finished.emit()

    def start(self, interval=2):
        if not self._started:
            self._started = True
            self.timer.start(interval, now=True)
