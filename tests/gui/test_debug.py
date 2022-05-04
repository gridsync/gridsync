# -*- coding: utf-8 -*-

from collections import deque
from unittest.mock import Mock

import pytest
from qtpy.QtCore import Qt

from gridsync.gui.debug import (
    DebugExporter,
    LogLoader,
    header,
    system,
    warning_text,
)


def test_system_module_variable_is_not_none():
    assert system is not None


def test_header_module_variable_is_not_none():
    assert header is not None


def test_warning_text_module_variable_is_not_none():
    assert warning_text is not None


@pytest.fixture
def core():
    fake_core = Mock()
    fake_core.tahoe_version = "9.999"
    fake_core.log_deque = deque(["debug msg 1", "/test/tahoe", "debug msg 3"])
    fake_gateway = Mock()
    fake_gateway.executable = "/test/tahoe"
    fake_gateway.name = "TestGridOne"
    fake_gateway.newscap = "URI:NEWSCAP"
    fake_gateway.magic_folder = Mock()
    fake_gateway.magic_folder.get_log_messages = Mock(
        return_value=['{"test": 123}']
    )
    fake_gateway.magic_folder.magic_folders = {}
    fake_gateway.get_streamed_log_messages = Mock(
        return_value=['{"test": 123}']
    )
    fake_gateway.get_settings = Mock(return_value={})
    fake_core.gateways = [fake_gateway]
    fake_core.gui.main_window.gateways = fake_core.gateways
    return fake_core


def test_log_loader_load_content(core):
    log_loader = LogLoader(core)
    log_loader.load()
    assert core.gateways[0].executable in log_loader.content


def test_log_loader_load_filtered_content(core):
    log_loader = LogLoader(core)
    log_loader.load()
    assert core.gateways[0].executable not in log_loader.filtered_content


def test_log_loader_load_warning_text_in_content(core):
    log_loader = LogLoader(core)
    log_loader.load()
    assert warning_text in log_loader.content


def test_log_loader_load_warning_text_in_filtered_content(core):
    log_loader = LogLoader(core)
    log_loader.load()
    assert warning_text in log_loader.filtered_content


@pytest.mark.parametrize(
    "checkbox_state, expected_content",
    [
        (Qt.Unchecked, "unfiltered"),
        (Qt.PartiallyChecked, "unfiltered"),
        (Qt.Checked, "filtered"),
    ],
)
def test_debug_exporter_on_checkbox_state_changed_toggle_content(
    checkbox_state, expected_content
):
    de = DebugExporter(None)
    de.log_loader.content = "unfiltered"
    de.log_loader.filtered_content = "filtered"
    de.on_checkbox_state_changed(checkbox_state)
    assert de.plaintextedit.toPlainText() == expected_content


def test_debug_exporter_on_checkbox_state_changed_keep_scrollbar_position():
    de = DebugExporter(None)
    fake_scrollbar = Mock()
    fake_scrollbar.value = Mock(return_value=99)
    fake_setValue = Mock()
    fake_scrollbar.setValue = fake_setValue
    de.scrollbar = fake_scrollbar
    de.on_checkbox_state_changed(0)
    assert de.scrollbar.setValue.call_args[0][0] == 99


def test_debug_exporter_on_info_button_clicked(monkeypatch):
    de = DebugExporter(None)
    fake_msgbox = Mock()
    monkeypatch.setattr("gridsync.gui.debug.QMessageBox", fake_msgbox)
    de.on_filter_info_button_clicked()
    assert fake_msgbox.called


def test_debug_exporter_load_content(core, qtbot):
    de = DebugExporter(core)
    de.checkbox.setCheckState(Qt.Unchecked)  # Filter off
    with qtbot.wait_signal(de.log_loader.done):
        de.load()
    assert core.gateways[0].executable in de.plaintextedit.toPlainText()


def test_debug_exporter_load_filtered_content(core, qtbot):
    de = DebugExporter(core)
    de.checkbox.setCheckState(Qt.Checked)  # Filter on
    with qtbot.wait_signal(de.log_loader.done):
        de.load()
    assert core.gateways[0].executable not in de.plaintextedit.toPlainText()


def test_debug_exporter_load_warning_text_in_content(core, qtbot):
    de = DebugExporter(core)
    de.checkbox.setCheckState(Qt.Unchecked)  # Filter off
    with qtbot.wait_signal(de.log_loader.done):
        de.load()
    assert warning_text in de.plaintextedit.toPlainText()


def test_debug_exporter_load_warning_text_in_filtered_content(core, qtbot):
    de = DebugExporter(core)
    de.checkbox.setCheckState(Qt.Checked)  # Filter on
    with qtbot.wait_signal(de.log_loader.done):
        de.load()
    assert warning_text in de.plaintextedit.toPlainText()


def test_debug_exporter_load_return_early_thread_running(core, qtbot):
    de = DebugExporter(core)
    de.log_loader_thread = Mock()
    de.log_loader_thread.isRunning(return_value=True)
    with qtbot.wait_signal(de.log_loader.done, raising=False, timeout=250):
        de.load()
    assert de.log_loader_thread.start.call_count == 0


def test_debug_exporter_copy_to_clipboard(monkeypatch):
    de = DebugExporter(None)
    de.plaintextedit.setPlainText("TESTING123")
    fake_set_clipboard_text = Mock()
    monkeypatch.setattr(
        "gridsync.gui.debug.set_clipboard_text", fake_set_clipboard_text
    )
    monkeypatch.setattr("gridsync.gui.debug.get_clipboard_modes", lambda: [1])
    de.copy_to_clipboard()
    assert fake_set_clipboard_text.call_args[0] == ("TESTING123", 1)


def test_debug_exporter_export_to_file_no_dest_return(monkeypatch, tmpdir):
    de = DebugExporter(None)
    de.close = Mock()
    fake_get_save_file_name = Mock(return_value=(None, None))
    monkeypatch.setattr(
        "gridsync.gui.debug.QFileDialog.getSaveFileName",
        fake_get_save_file_name,
    )
    de.export_to_file()
    assert de.close.call_count == 0


def test_debug_exporter_export_to_file_success(monkeypatch, tmpdir):
    de = DebugExporter(None)
    expected_content = "EXPECTED_CONTENT"
    de.plaintextedit.setPlainText(expected_content)
    dest = str(tmpdir.join("log.txt"))
    fake_get_save_file_name = Mock(return_value=(dest, None))
    monkeypatch.setattr(
        "gridsync.gui.debug.QFileDialog.getSaveFileName",
        fake_get_save_file_name,
    )
    de.export_to_file()
    with open(dest) as f:
        assert f.read() == expected_content


def test_debug_exporter_export_to_file_failure(monkeypatch, tmpdir):
    de = DebugExporter(None)
    de.plaintextedit.setPlainText("TEST_CONTENT")
    dest = str(tmpdir.join("log.txt"))
    fake_getSaveFileName = Mock(return_value=(dest, None))
    monkeypatch.setattr(
        "gridsync.gui.debug.QFileDialog.getSaveFileName", fake_getSaveFileName
    )
    error_message = "Something Bad Happened"
    fake_to_plain_text = Mock(side_effect=OSError(error_message))
    monkeypatch.setattr(
        "gridsync.gui.debug.QPlainTextEdit.toPlainText", fake_to_plain_text
    )
    fake_error = Mock()
    monkeypatch.setattr("gridsync.gui.debug.error", fake_error)
    de.export_to_file()
    assert fake_error.call_args[0][2] == error_message
