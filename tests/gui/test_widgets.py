# -*- coding: utf-8 -*-

from gridsync.gui.widgets import EncodingParameters, TahoeConfigForm


def test_decrement_shares_needed_with_shares_total():
    widget = EncodingParameters()
    widget.needed_spinbox.setValue(3)
    widget.total_spinbox.setValue(1)
    assert widget.needed_spinbox.value() == 1


def test_decrement_shares_happy_with_shares_total():
    widget = EncodingParameters()
    widget.happy_spinbox.setValue(7)
    widget.total_spinbox.setValue(1)
    assert widget.happy_spinbox.value() == 1


def test_increment_shares_total_with_shares_needed():
    widget = EncodingParameters()
    widget.total_spinbox.setValue(1)
    widget.needed_spinbox.setValue(3)
    assert widget.total_spinbox.value() == 3


def test_increment_shares_total_with_shares_happy():
    widget = EncodingParameters()
    widget.total_spinbox.setValue(1)
    widget.happy_spinbox.setValue(7)
    assert widget.total_spinbox.value() == 7


def test_tahoe_config_form_get_settings():
    widget = TahoeConfigForm()
    widget.connection_settings.introducer_text_edit.setPlainText("test")
    assert widget.get_settings()["introducer"] == "test"
