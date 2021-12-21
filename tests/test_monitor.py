# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, Mock, call
from datetime import datetime, timedelta
from pathlib import Path

from pytest_twisted import inlineCallbacks

from gridsync.monitor import GridChecker, Monitor, ZKAPChecker


@inlineCallbacks
def test_grid_checker_emit_space_updated(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.space_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [1234]


@inlineCallbacks
def test_grid_checker_emit_nodes_updated_(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.nodes_updated) as blocker:
        yield gc.do_check()
    assert blocker.args == [8, 10]


@inlineCallbacks
def test_grid_checker_emit_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(8, 10, 1234))
    with qtbot.wait_signal(gc.connected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_emit_disconnected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=7))
    gc.gateway.get_grid_status = MagicMock(return_value=(5, 10, 1234))
    gc.is_connected = True
    with qtbot.wait_signal(gc.disconnected):
        yield gc.do_check()


@inlineCallbacks
def test_grid_checker_not_connected(qtbot):
    gc = GridChecker(MagicMock(shares_happy=0))
    gc.gateway.get_grid_status = MagicMock(return_value=None)
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
