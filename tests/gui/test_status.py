# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest

from gridsync.gui.status import StatusPanel
from gridsync.magic_folder import MagicFolderStatus
from gridsync.tahoe import Tahoe


def test_status_panel_hide_tor_button(fake_tahoe):
    # gateway = MagicMock()
    fake_tahoe.use_tor = False
    sp = StatusPanel(fake_tahoe, MagicMock())
    assert sp.tor_button.isHidden() is True


@pytest.mark.parametrize(
    "num_connected, shares_happy, overall_status, use_tor, text",
    [
        [0, 0, MagicFolderStatus.LOADING, False, "Connecting to TestGrid..."],
        [
            0,
            0,
            MagicFolderStatus.LOADING,
            True,
            "Connecting to TestGrid via Tor...",
        ],
        [
            3,
            5,
            MagicFolderStatus.WAITING,
            False,
            "Connecting to TestGrid (3/5)...",
        ],
        [
            3,
            5,
            MagicFolderStatus.WAITING,
            True,
            "Connecting to TestGrid (3/5) via Tor...",
        ],
        [
            5,
            5,
            MagicFolderStatus.WAITING,
            True,
            "Connected to TestGrid via Tor",
        ],
        [5, 5, MagicFolderStatus.SYNCING, False, "Syncing"],
        [5, 5, MagicFolderStatus.ERROR, False, "Error syncing folder"],
        [5, 5, MagicFolderStatus.UP_TO_DATE, False, "Up to date"],
    ],
)
def test_on_sync_status_updated(
    num_connected, shares_happy, overall_status, use_tor, text, fake_tahoe
):
    fake_tahoe.shares_happy = shares_happy
    fake_tahoe.use_tor = use_tor
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.num_connected = num_connected
    sp.on_sync_status_updated(overall_status)
    assert sp.status_label.text() == text


@pytest.mark.parametrize(
    "num_connected,num_known,available_space,tooltip",
    [
        [1, 2, 3, "Connected to 1 of 2 storage nodes\n3 available"],
        [1, 2, None, "Connected to 1 of 2 storage nodes"],
    ],
)
def test__update_grid_info(
    num_connected, num_known, available_space, tooltip, fake_tahoe
):
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.num_connected = num_connected
    sp.num_known = num_known
    sp.available_space = available_space
    sp._update_status_label()
    assert sp.status_label.toolTip() == tooltip


def test_on_space_updated_humanize(fake_tahoe):
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_space_updated(1024)
    assert sp.available_space == "1.0 kB"


def test_on_nodes_updated_set_num_connected_and_num_known(fake_tahoe):
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert (sp.num_connected, sp.num_known) == (4, 5)


def test_on_nodes_updated_grid_name_in_status_label(fake_tahoe):
    fake_tahoe.use_tor = False
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert sp.status_label.text() == "Connected to TestGrid"


def test_on_nodes_updated_tor_usage_in_status_label(fake_tahoe):
    fake_tahoe.use_tor = True
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert sp.status_label.text() == "Connected to TestGrid via Tor"


def test_on_nodes_updated_node_count_in_status_label_when_connecting(
    fake_tahoe,
):
    fake_tahoe.shares_happy = 5
    fake_tahoe.use_tor = False
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert sp.status_label.text() == "Connecting to TestGrid (4/5)..."


def test_days_remaining_updated_signal_does_not_raise_overflow_error(gui):
    sp = StatusPanel(Tahoe(), gui)
    sp.gateway.monitor.days_remaining_updated.emit(2**256)
    assert True
