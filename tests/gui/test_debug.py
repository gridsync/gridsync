# -*- coding: utf-8 -*-

import os
from unittest.mock import Mock

import pytest
from PyQt5.QtCore import Qt

from gridsync.gui.debug import system, header, warning_text, DebugExporter


def test_system_module_variable_is_not_none():
    assert system is not None


def test_header_module_variable_is_not_none():
    assert header is not None


def test_warning_text_module_variable_is_not_none():
    assert warning_text is not None


def test_debug_exporter_init(qtbot):
    assert qtbot


@pytest.mark.parametrize(
    'scrollbar_value, scrolbar_maximum, is_enabled',
    [
        (99, 99, True),
        (0, 0, True),
        (50, 99, False),
    ]
)
def test_debug_exporter_maybe_enable_buttons(
        scrollbar_value, scrolbar_maximum, is_enabled):
    de = DebugExporter(None)
    fake_scrollbar = Mock()
    fake_scrollbar.maximum = Mock(return_value=scrolbar_maximum)
    de.scrollbar = fake_scrollbar
    de.maybe_enable_buttons(scrollbar_value)
    assert de.copy_button.isEnabled() == is_enabled


@pytest.mark.parametrize(
    'checkbox_state, expected_content',
    [
        (Qt.Unchecked, 'unfiltered'),
        (Qt.PartiallyChecked, 'unfiltered'),
        (Qt.Checked, 'filtered'),
    ]
)
def test_debug_exporter_on_checkbox_state_changed_toggle_content(
        checkbox_state, expected_content):
    de = DebugExporter(None)
    de.content = 'unfiltered'
    de.filtered_content = 'filtered'
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
    monkeypatch.setattr('gridsync.gui.debug.QMessageBox', fake_msgbox)
    de.on_filter_info_button_clicked()
    assert fake_msgbox.called


def test_debug_exporter_copy_to_clipboard(monkeypatch):
    de = DebugExporter(None)
    de.plaintextedit.setPlainText('TESTING123')
    fake_set_clipboard_text = Mock()
    monkeypatch.setattr(
        'gridsync.gui.debug.set_clipboard_text', fake_set_clipboard_text)
    monkeypatch.setattr('gridsync.gui.debug.get_clipboard_modes', lambda: [1])
    de.copy_to_clipboard()
    assert fake_set_clipboard_text.call_args[0] == ('TESTING123', 1)


def test_debug_exporter_export_to_file_no_dest_return(monkeypatch, tmpdir):
    de = DebugExporter(None)
    de.close = Mock()
    fake_get_save_file_name = Mock(return_value=(None, None))
    monkeypatch.setattr(
        'gridsync.gui.debug.QFileDialog.getSaveFileName',
        fake_get_save_file_name
    )
    de.export_to_file()
    assert de.close.call_count == 0


def test_debug_exporter_export_to_file_success(monkeypatch, tmpdir):
    de = DebugExporter(None)
    expected_content = 'EXPECTED_CONTENT'
    de.plaintextedit.setPlainText(expected_content)
    dest = str(tmpdir.join("log.txt"))
    fake_get_save_file_name = Mock(return_value=(dest, None))
    monkeypatch.setattr(
        'gridsync.gui.debug.QFileDialog.getSaveFileName',
        fake_get_save_file_name
    )
    de.export_to_file()
    with open(dest) as f:
        assert f.read() == expected_content


def test_debug_exporter_export_to_file_failure(monkeypatch, tmpdir):
    de = DebugExporter(None)
    de.plaintextedit.setPlainText('TEST_CONTENT')
    dest = str(tmpdir.join("log.txt"))
    fake_getSaveFileName = Mock(return_value=(dest, None))
    monkeypatch.setattr(
        'gridsync.gui.debug.QFileDialog.getSaveFileName', fake_getSaveFileName)
    error_message = 'Something Bad Happened'
    fake_to_plain_text = Mock(side_effect=OSError(error_message))
    monkeypatch.setattr(
        'gridsync.gui.debug.QPlainTextEdit.toPlainText', fake_to_plain_text)
    fake_error = Mock()
    monkeypatch.setattr('gridsync.gui.debug.error', fake_error)
    de.export_to_file()
    assert fake_error.call_args[0][2] == error_message
