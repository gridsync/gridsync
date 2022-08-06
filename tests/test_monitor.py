# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable, TypeVar
from unittest.mock import MagicMock, Mock, call

from pytest_twisted import inlineCallbacks

from gridsync.monitor import GridChecker, Monitor, ZKAPChecker, _parse_vouchers

T = TypeVar("T")


def fake_grid_status(status: T) -> Callable[[], Awaitable[T]]:
    async def get_grid_status() -> T:
        return status

    return get_grid_status


@inlineCallbacks
def test_grid_checker_emit_space_updated(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = fake_grid_status((8, 10, 1234))
    with qtbot.wait_signal(gc.space_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [1234]


@inlineCallbacks
def test_grid_checker_emit_nodes_updated_(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = fake_grid_status((8, 10, 1234))
    with qtbot.wait_signal(gc.nodes_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [8, 10]


@inlineCallbacks
def test_grid_checker_emit_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = fake_grid_status((8, 10, 1234))
    with qtbot.wait_signal(gc.connected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_emit_disconnected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = fake_grid_status((5, 10, 1234))
    gc.is_connected = True
    with qtbot.wait_signal(gc.disconnected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_not_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=0))
    gc.gateway.get_grid_status = fake_grid_status(None)
    yield gc.do_check()
    assert gc.num_connected == 0


@inlineCallbacks
def test_monitor_emit_check_finished(monkeypatch, qtbot):
    gateway = Mock(zkap_auth_required=False)
    monitor = Monitor(gateway)
    monitor.grid_checker = MagicMock()
    with qtbot.wait_signal(monitor.check_finished):
        yield monitor.do_checks()


def test_monitor_start():
    monitor = Monitor(MagicMock())
    monitor.timer = MagicMock()
    monitor.start()
    assert monitor.timer.mock_calls == [call.start(2, now=True)]


def test_monitor_multiple_start():
    """
    Calling ``Monitor.start`` multiple times has no effects beyond those of
    calling it once.
    """
    monitor = Monitor(MagicMock())
    monitor.timer = MagicMock()
    monitor.start()
    monitor.start()
    assert monitor.timer.mock_calls == [call.start(2, now=True)]


def test_zkaps_update_last_redeemed(tahoe):
    """
    ``ZKAPChecker._maybe_load_last_redeemed`` emits the contents of
    ``last-redeemed`` to ``zkaps_redeemed`` when the last-redeemed time
    advances.
    """
    now = datetime(2021, 12, 21, 13, 23, 50)
    zkaps = Path(tahoe.nodedir, "private", "zkaps")
    zkaps.mkdir()
    last_redeemed_path = Path(zkaps, "last-redeemed")
    with open(last_redeemed_path, "w", encoding="utf-8") as f:
        f.write(now.isoformat())

    zkaps_redeemed = []

    checker = ZKAPChecker(tahoe)
    checker.zkaps_redeemed.connect(zkaps_redeemed.append)

    checker._maybe_load_last_redeemed()
    assert zkaps_redeemed == [now.isoformat()]

    # Nothing has changed so it is not emitted again.
    checker._maybe_load_last_redeemed()
    assert zkaps_redeemed == [now.isoformat()]

    # Advance it so that it is emitted again.
    later = now + timedelta(seconds=1)
    with open(last_redeemed_path, "w", encoding="utf-8") as f:
        f.write(later.isoformat())

    checker._maybe_load_last_redeemed()
    assert zkaps_redeemed == [now.isoformat(), later.isoformat()]


def test__parse_voucher_contains_redeeming_vouchers(tahoe):
    vouchers = [
        {
            "created": "2022-01-17T13:53:16.865887",
            "expected-tokens": 50000,
            "number": "0MH30nxh9iup727nTi3u51Ir9HcQYIM8",
            "state": {
                "counter": 15,
                "name": "redeeming",
                "started": "2022-01-17T13:55:15.177781",
            },
            "version": 1,
        }
    ]
    now = datetime(2021, 12, 21, 13, 23, 50)
    parsed = _parse_vouchers(vouchers, now)
    assert parsed.redeeming_vouchers == ["0MH30nxh9iup727nTi3u51Ir9HcQYIM8"]


def test__update_redeeming_vouchers_emits_redeeming_vouchers_updated(tahoe):
    vouchers = [
        {
            "created": "2022-01-17T13:53:16.865887",
            "expected-tokens": 50000,
            "number": "0MH30nxh9iup727nTi3u51Ir9HcQYIM8",
            "state": {
                "counter": 15,
                "name": "redeeming",
                "started": "2022-01-17T13:55:15.177781",
            },
            "version": 1,
        }
    ]
    now = datetime(2021, 12, 21, 13, 23, 50)
    parsed = _parse_vouchers(vouchers, now)
    redeeming_vouchers = []
    checker = ZKAPChecker(tahoe)
    checker.redeeming_vouchers_updated.connect(redeeming_vouchers.extend)
    checker._update_redeeming_vouchers(parsed.redeeming_vouchers)
    assert redeeming_vouchers == ["0MH30nxh9iup727nTi3u51Ir9HcQYIM8"]
