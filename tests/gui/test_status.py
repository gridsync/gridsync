# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest

from gridsync.gui.status import StatusPanel


def test_status_panel_hide_tor_button():
    gateway = MagicMock()
    gateway.use_tor = False
    sp = StatusPanel(gateway, MagicMock())
    assert sp.tor_button.isHidden() is True


@pytest.mark.parametrize(
    "state,text", [[0, "Connecting..."], [1, "Syncing"], [2, "Up to date"]]
)
def test_on_sync_state_updated(state, text):
    sp = StatusPanel(MagicMock(), MagicMock())
    sp.on_sync_state_updated(state)
    assert sp.status_label.text() == text


@pytest.mark.parametrize(
    "num_connected,num_known,available_space,tooltip",
    [
        [1, 2, 3, "Connected to 1 of 2 storage nodes\n3 available"],
        [1, 2, None, "Connected to 1 of 2 storage nodes"],
    ],
)
def test__update_grid_info(num_connected, num_known, available_space, tooltip):
    sp = StatusPanel(MagicMock(), MagicMock())
    sp.num_connected = num_connected
    sp.num_known = num_known
    sp.available_space = available_space
    sp._update_grid_info_tooltip()
    assert sp.globe_action.toolTip() == tooltip


def test_on_space_updated_humanize():
    sp = StatusPanel(MagicMock(), MagicMock())
    sp.on_space_updated(1024)
    assert sp.available_space == "1.0 kB"


def test_on_nodes_updated():
    sp = StatusPanel(MagicMock(), MagicMock())
    sp.on_nodes_updated(4, 5)
    assert (sp.num_connected, sp.num_known) == (4, 5)
