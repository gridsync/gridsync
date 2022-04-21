# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import attr
from qtpy.QtCore import QObject, Signal
from twisted.internet.defer import inlineCallbacks
from twisted.internet.error import ConnectError
from twisted.internet.task import LoopingCall

from gridsync.errors import TahoeWebError


class GridChecker(QObject):

    connected = Signal()
    disconnected = Signal()
    nodes_updated = Signal(int, int)
    space_updated = Signal(object)

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


@attr.s
class _VoucherParse:
    """
    :ivar total_tokens: A number of spendable tokens that are expected to
        exist due to all of the vouchers that have already been redeemed.

    :ivar unpaid_vouchers: A list of voucher identifiers which are believed to
        not yet have been paid for.

    :ivar unpaid_vouchers: A list of voucher identifiers which are currently
        in the process of being redeemed for tokens.

    :ivar zkaps_last_redeemed: An ISO8601 datetime string giving the latest
        time at which a voucher was seen to have been redeemed.  If no
        redemption was seen then the value is an empty string instead.
    """

    total_tokens = attr.ib()
    unpaid_vouchers = attr.ib()
    redeeming_vouchers = attr.ib()
    zkaps_last_redeemed = attr.ib()


def _parse_vouchers(
    vouchers: List[dict],
    time_started: datetime,
) -> _VoucherParse:
    """
    Examine a list of vouchers states from ZKAPAuthorizer to derive certain
    facts about the overall state.

    :param vouchers: A representation of the vouchers to inspect.  This is
        expected to be a value like the one returned by ZKAPAuthorizer's **GET
        /storage-plugins/privatestorageio-zkapauthz-v1/voucher** endpoint.

    :param time_started: The time at which the currently active
        ``ZKAPChecker`` began monitoring the state of vouchers in the
        ZKAPAuthorizer-enabled Tahoe-LAFS node.  This is used to exclude
        vouchers older than this checker, the redemption status of which this
        function cannot currently interpret.

    :return: A summary of the state of the vouchers and the number of tokens
        available.
    """
    total = 0
    zkaps_last_redeemed = ""
    unpaid_vouchers = set()
    redeeming_vouchers = set()
    for voucher in vouchers:
        number = voucher["number"]
        state = voucher["state"]
        name = state["name"]
        if name == "unpaid":  # or "redeeming"?
            # XXX There is no reliable way of knowing whether the user
            # intends to pay for an older voucher -- i.e., one that
            # was created before the application started --
            # so ignore those older vouchers for now and only monitor
            # those vouchers that were created during *this* run.
            created = voucher["created"]
            if created is None:
                continue
            time_created = datetime.fromisoformat(created)
            if time_created > time_started:
                unpaid_vouchers.add(number)
        elif name == "redeeming" and state.get("counter", 0):
            redeeming_vouchers.add(number)
        elif name == "redeemed":
            total += state["token-count"]
            finished = state["finished"]
            zkaps_last_redeemed = max(zkaps_last_redeemed, finished)
    return _VoucherParse(
        total,
        sorted(unpaid_vouchers),
        sorted(redeeming_vouchers),
        zkaps_last_redeemed,
    )


class ZKAPChecker(QObject):

    zkaps_updated = Signal(int, int)  # used, remaining
    zkaps_available = Signal()
    zkaps_redeemed = Signal(str)  # timestamp
    zkaps_renewal_cost_updated = Signal(int)
    zkaps_price_updated = Signal(int, int)
    days_remaining_updated = Signal(int)
    unpaid_vouchers_updated = Signal(list)
    redeeming_vouchers_updated = Signal(list)
    low_zkaps_warning = Signal()

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self._time_started: Optional[datetime] = None
        self._low_zkaps_warning_shown: bool = False

        self.zkaps_remaining: int = 0
        self.zkaps_total: int = 0
        self.zkaps_last_redeemed: str = "0"
        self.zkaps_renewal_cost: int = 0
        self.days_remaining: int = 0
        self.unpaid_vouchers: list = []
        self.redeeming_vouchers: list = []

    def consumption_rate(self):
        zkaps_spent = self.zkaps_total - self.zkaps_remaining
        # XXX zkaps_last_redeemed starts as "0" which cannot be parsed as an
        # ISO8601 datetime.
        last_redeemed = datetime.fromisoformat(self.zkaps_last_redeemed)
        now = datetime.now()
        seconds = datetime.timestamp(now) - datetime.timestamp(last_redeemed)
        consumption_rate = zkaps_spent / seconds
        return consumption_rate

    def _maybe_emit_low_zkaps_warning(self):
        if (
            self.zkaps_total
            and self.days_remaining
            and not self._low_zkaps_warning_shown
        ):
            pct_used = 1 - (self.zkaps_remaining / self.zkaps_total)
            if pct_used >= 0.9 or self.days_remaining <= 60:
                self.low_zkaps_warning.emit()
                self._low_zkaps_warning_shown = True

    def _maybe_load_last_redeemed(self) -> None:
        try:
            with open(
                Path(
                    self.gateway.nodedir, "private", "zkaps", "last-redeemed"
                ),
                encoding="utf-8",
            ) as f:
                last_redeemed = f.read()
        except FileNotFoundError:
            return
        self._update_zkaps_last_redeemed(last_redeemed)

    def _update_unpaid_vouchers(self, unpaid_vouchers):
        """
        Record and propagate notification about the set of unpaid vouchers
        changing, if it has.
        """
        if unpaid_vouchers != self.unpaid_vouchers:
            self.unpaid_vouchers = unpaid_vouchers
            self.unpaid_vouchers_updated.emit(self.unpaid_vouchers)

    def _update_redeeming_vouchers(self, redeeming_vouchers):
        """
        Record and propagate notification about the set of redeeming vouchers
        changing, if it has.
        """
        if redeeming_vouchers != self.redeeming_vouchers:
            self.redeeming_vouchers = redeeming_vouchers
            self.redeeming_vouchers_updated.emit(self.redeeming_vouchers)

    def _update_zkaps_last_redeemed(self, zkaps_last_redeemed):
        """
        Record and propagate notification about last redemption time moving
        forward, if it has.
        """
        if zkaps_last_redeemed > self.zkaps_last_redeemed:
            self.zkaps_last_redeemed = zkaps_last_redeemed
            self.zkaps_redeemed.emit(self.zkaps_last_redeemed)

    def _maybe_load_last_total(self) -> int:
        try:
            with open(
                Path(self.gateway.nodedir, "private", "zkaps", "last-total"),
                encoding="utf-8",
            ) as f:
                return int(f.read())
        except FileNotFoundError:
            return 0

    def emit_zkaps_updated(self, remaining, total):
        used = total - remaining
        batch_size = self.gateway.zkapauthorizer.zkap_batch_size
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
        self.update_price()  # XXX Maybe too expensive to call here?

    @inlineCallbacks
    def update_price(self):
        # ZKAPAuthorizer.get_price() can fail with an HTTP 410 error if
        # called too soon during tahoe startup so wait until connected
        yield self.gateway.await_ready()
        # MagicFolder.get_all_object_sizes() will fail with an "API
        # token not found" error if called before MagicFolder starts
        yield self.gateway.magic_folder.await_running()
        p = yield self.gateway.zkapauthorizer.get_price()
        price = p.get("price", 0)
        period = p.get("period", 0)
        self.zkaps_price_updated.emit(price, period)
        if price and period:
            seconds_remaining = self.zkaps_remaining / price * period
            self.days_remaining = int(seconds_remaining / 86400)
            self.days_remaining_updated.emit(self.days_remaining)

    @inlineCallbacks  # noqa: max-complexity
    def do_check(self):  # noqa: max-complexity
        # XXX/TODO This is all truly awful; clean this up.
        if self._time_started is None:
            self._time_started = datetime.now()
        if not self.gateway.zkap_auth_required or self.gateway.nodeurl is None:
            # Either the node doesn't use ZKAPs or isn't running.
            return
        try:
            vouchers = yield self.gateway.zkapauthorizer.get_vouchers()
        except (ConnectError, TahoeWebError):
            return  # XXX
        if not vouchers:
            if self.zkaps_last_redeemed == "0":
                self._maybe_load_last_redeemed()
            else:
                self.emit_zkaps_updated(self.zkaps_remaining, self.zkaps_total)
        parse = _parse_vouchers(
            vouchers,
            self._time_started,
        )
        total = parse.total_tokens
        self._update_unpaid_vouchers(parse.unpaid_vouchers)
        self._update_redeeming_vouchers(parse.redeeming_vouchers)
        self._update_zkaps_last_redeemed(parse.zkaps_last_redeemed)

        try:
            zkaps = yield self.gateway.zkapauthorizer.get_zkaps(limit=1)
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
            self.emit_zkaps_updated(remaining, total)
            if not self.zkaps_remaining and remaining:
                # Some (non-zero) amount of ZKAPs are now available --
                # in other words, the grid is now "writeable"
                self.zkaps_available.emit()
            self.zkaps_remaining = remaining
            self.zkaps_total = total
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
        # daily_cost = self.zkaps_renewal_cost / 27
        # try:
        #    days_remaining = int(self.zkaps_remaining / daily_cost)
        # except ZeroDivisionError:
        #    return
        # if days_remaining != self.days_remaining:
        #    self.days_remaining = days_remaining
        #    self.days_remaining_updated.emit(days_remaining)
        self._maybe_emit_low_zkaps_warning()


class Monitor(QObject):
    """
    Look at ZKAPAuthorizer and on-grid state and detect changes in interesting
    things.

    :ivar bool _started: Whether or not ``start`` has already been called.

    :ivar Signal zkaps_updated: A signal that is emitted periodically when
        we notice that the number of available or total ZKAPs has changed.  Is
        it emitted near startup?  I don't know.

    :ivar zkaps_redeemed: A signal that is emitted whenever we notice that the
        timestamp of the most recent voucher redemption has changed.  Also
        maybe it is emitted near startup when we learn the current timestamp
        since we don't have a previous value to compare it to.
    """

    _started = False

    connected = Signal()
    disconnected = Signal()
    nodes_updated = Signal(int, int)
    space_updated = Signal(object)

    check_finished = Signal()

    zkaps_updated = Signal(int, int)
    zkaps_available = Signal()
    zkaps_redeemed = Signal(str)
    zkaps_renewal_cost_updated = Signal(int)
    zkaps_price_updated = Signal(int, int)
    days_remaining_updated = Signal(int)
    unpaid_vouchers_updated = Signal(list)
    redeeming_vouchers_updated = Signal(list)
    low_zkaps_warning = Signal()

    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway
        self.timer = LoopingCall(self.do_checks)

        self.grid_checker = GridChecker(self.gateway)
        self.grid_checker.connected.connect(self.connected.emit)
        self.grid_checker.disconnected.connect(self.disconnected.emit)
        self.grid_checker.nodes_updated.connect(self.nodes_updated.emit)
        self.grid_checker.space_updated.connect(self.space_updated.emit)

        self.zkap_checker = ZKAPChecker(self.gateway)
        self.zkap_checker.zkaps_updated.connect(self.zkaps_updated.emit)
        self.zkap_checker.zkaps_available.connect(self.zkaps_available.emit)
        self.zkap_checker.zkaps_redeemed.connect(self.zkaps_redeemed.emit)
        self.zkap_checker.zkaps_renewal_cost_updated.connect(
            self.zkaps_renewal_cost_updated.emit
        )
        self.zkap_checker.zkaps_price_updated.connect(self.zkaps_price_updated)
        self.zkap_checker.days_remaining_updated.connect(
            self.days_remaining_updated.emit
        )
        self.zkap_checker.unpaid_vouchers_updated.connect(
            self.unpaid_vouchers_updated.emit
        )
        self.zkap_checker.redeeming_vouchers_updated.connect(
            self.redeeming_vouchers_updated.emit
        )
        self.zkap_checker.low_zkaps_warning.connect(
            self.low_zkaps_warning.emit
        )

    @inlineCallbacks
    def do_checks(self):
        yield self.zkap_checker.do_check()
        yield self.grid_checker.do_check()
        self.check_finished.emit()

    def start(self, interval=2):
        if not self._started:
            self._started = True
            self.timer.start(interval, now=True)
