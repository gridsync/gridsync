# -*- coding: utf-8 -*-

from unittest.mock import MagicMock, Mock

import pytest

from gridsync.gui.status import StatusPanel


@pytest.fixture()
def fake_tahoe():
    t = Mock()
    t.name = "TestGrid"
    t.shares_happy = 3
    return t


def test_status_panel_hide_tor_button(fake_tahoe):
    # gateway = MagicMock()
    fake_tahoe.use_tor = False
    sp = StatusPanel(fake_tahoe, MagicMock())
    assert sp.tor_button.isHidden() is True


@pytest.mark.parametrize(
    "state,num_connected,shares_happy,text",
    [
        [0, 0, 0, "Connecting to TestGrid..."],
        [0, 3, 5, "Connecting to TestGrid (3/5)..."],
        [1, 5, 5, "Syncing"],
        [2, 5, 5, "Up to date"],
    ],
)
def test_on_sync_state_updated(
    state, num_connected, shares_happy, text, fake_tahoe
):
    fake_tahoe.shares_happy = shares_happy
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.num_connected = num_connected
    sp.on_sync_state_updated(state)
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
    # fake_tahoe = Mock()
    # fake_tahoe.name = "TestGrid"
    # fake_tahoe.shares_happy = 3
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert (sp.num_connected, sp.num_known) == (4, 5)


def test_on_nodes_updated_grid_name_in_status_label(fake_tahoe):
    # fake_tahoe = Mock()
    # fake_tahoe.name = "TestGrid"
    # fake_tahoe.shares_happy = 3
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert sp.status_label.text() == "Connected to TestGrid"


def test_on_nodes_updated_node_count_in_status_label_when_connecting(
    fake_tahoe,
):
    # fake_tahoe = Mock()
    # fake_tahoe.name = "TestGrid"
    fake_tahoe.shares_happy = 5
    sp = StatusPanel(fake_tahoe, MagicMock())
    sp.on_nodes_updated(4, 5)
    assert sp.status_label.text() == "Connecting to TestGrid (4/5)..."
