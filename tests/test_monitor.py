# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, Mock, call

import pytest
from pytest_twisted import inlineCallbacks

from gridsync.monitor import GridChecker, Monitor


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
