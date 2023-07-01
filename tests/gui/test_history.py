import os
import shutil
from unittest.mock import Mock, call

import pytest

from gridsync.gui.history import (
    HistoryItemWidget,
    HistoryListWidget,
    HistoryView,
)


@pytest.fixture(scope="function")
def hiw(tmpdir_factory):
    src = os.path.join(os.getcwd(), "gridsync", "resources", "pixel.png")
    dst = str(tmpdir_factory.mktemp("test-magic-folder"))
    shutil.copy(src, dst)
    gateway = Mock()
    gateway.magic_folder.get_directory.return_value = dst
    return HistoryItemWidget(
        "Added", "pixel.png", 123456789, HistoryListWidget(gateway)
    )


def test_history_item_widget_init(hiw):
    assert hiw


def test_history_item_widget__do_load_thumbnail(hiw):
    hiw._do_load_thumbnail()
    assert hiw.icon.pixmap() is not None


def test_history_item_widget_load_thumbnail(hiw, monkeypatch):
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryItemWidget.isVisible", lambda _: True
    )
    hiw.load_thumbnail()
    assert hiw._thumbnail_loaded is True


def test_history_item_widget_unhilight(hiw):
    hiw.button.show()
    hiw.unhighlight()
    assert hiw.button.isHidden()


def test_history_item_widget_enter_event(hiw):
    hiw.enterEvent(None)
    assert hiw.parent().highlighted == hiw


def test_history_item_widget_enter_event_call_unhighlight(hiw):
    m = Mock()
    hiw.parent().highlighted = m
    hiw.enterEvent(None)
    assert m.method_calls == [call.unhighlight()]


def test_history_item_widget_enter_event_pass_runtime_error(hiw):
    hiw.parent().highlighted = Mock()
    hiw.parent().highlighted.unhighlight = Mock(side_effect=RuntimeError)
    hiw.enterEvent(None)
    assert hiw.parent().highlighted == hiw


@pytest.fixture(scope="function")
def hlw(tmpdir_factory):
    directory = str(tmpdir_factory.mktemp("test-magic-folder"))
    gateway = Mock()
    gateway.magic_folder.get_directory.return_value = directory
    return HistoryListWidget(gateway)


def test_history_list_widget_on_double_click(hlw, monkeypatch):
    m = Mock()
    monkeypatch.setattr("gridsync.gui.history.open_enclosing_folder", m)
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.itemWidget",
        Mock(
            return_value=HistoryItemWidget(
                "Added", "pixel.png", 123456789, hlw
            )
        ),
    )
    hlw.on_double_click(None)
    assert m.mock_calls


def test_history_list_widget_on_right_click(hlw, monkeypatch):
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.itemAt", Mock()
    )
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.itemWidget",
        Mock(
            return_value=HistoryItemWidget(
                "Added", "pixel.png", 123456789, hlw
            )
        ),
    )
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.viewport", Mock()
    )
    m = Mock()
    monkeypatch.setattr("gridsync.gui.history.QMenu", m)
    hlw.on_right_click(None)
    assert m.mock_calls


def test_history_list_widget_on_right_click_no_item_return(hlw, monkeypatch):
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.itemAt", lambda x, y: None
    )
    m = Mock()
    monkeypatch.setattr("gridsync.gui.history.QMenu", m)
    hlw.on_right_click(None)
    assert m.mock_calls == []


def test_history_list_widget_add_item(hlw):
    hlw.add_item("TestFolder", "Added", "pixel.png", 123456789)
    assert hlw.count() == 1


def test_history_list_widget_add_item_deduplicate(hlw):
    hlw.add_item("TestFolder", "Added", "pixel.png", 123456788)
    hlw.add_item("TestFolder", "Added", "pixel.png", 123456789)
    assert hlw.count() == 1


def test_history_list_widget_update_visible_widgets(hlw, monkeypatch):
    hlw.add_item("TestFolder", "Added", "pixel.png", 99999)
    m = Mock()
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryItemWidget.update_text", m
    )
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.isVisible", lambda _: True
    )
    hlw.update_visible_widgets()
    assert m.mock_calls == [call()]


def test_history_list_widget_update_visible_widgets_return(hlw, monkeypatch):
    hlw.add_item("TestFolder", "Added", "pixel.png", 99999)
    m = Mock()
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryItemWidget.update_text", m
    )
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.isVisible", lambda _: False
    )
    hlw.update_visible_widgets()
    assert m.mock_calls == []


def test_history_list_widget_update_visible_widgets_on_show_event(
    hlw, monkeypatch
):
    m = Mock()
    monkeypatch.setattr(
        "gridsync.gui.history.HistoryListWidget.update_visible_widgets", m
    )
    hlw.showEvent(None)
    assert m.mock_calls == [call()]


def test_history_view_init():
    mock_gateway = Mock()
    mock_gateway.shares_happy = 1
    hv = HistoryView(mock_gateway, Mock())
    assert hv
