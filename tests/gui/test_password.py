# -*- coding: utf-8 -*-

import pytest

from gridsync.gui.password import PasswordLineEdit, PasswordCreationWidget


@pytest.fixture(scope='module')
def password_line_edit():
    widget = PasswordLineEdit()
    return widget


@pytest.fixture(scope='module')
def password_line_creation_widget():
    widget = PasswordCreationWidget()
    return widget


def test_password_line_edit_toggle_visibility_on(password_line_edit):
    password_line_edit.action.triggered.emit()
    assert password_line_edit.echoMode() == PasswordLineEdit.Normal


def test_password_line_edit_toggle_visibility_off(password_line_edit):
    password_line_edit.action.triggered.emit()
    assert password_line_edit.echoMode() == PasswordLineEdit.Password


def test_password_creation_widget_very_weak(password_line_creation_widget):
    password_line_creation_widget.update_stats('test')
    assert password_line_creation_widget.progressbar.value() == 1


def test_password_creation_widget_weak(password_line_creation_widget):
    password_line_creation_widget.update_stats('test12345')
    assert password_line_creation_widget.progressbar.value() == 1


def test_password_creation_widget_alright(password_line_creation_widget):
    password_line_creation_widget.update_stats('testing 123 test')
    assert password_line_creation_widget.progressbar.value() == 2


def test_password_creation_widget_good(password_line_creation_widget):
    password_line_creation_widget.update_stats('testing 123 test !')
    assert password_line_creation_widget.progressbar.value() == 3


def test_password_creation_widget_excellent(password_line_creation_widget):
    password_line_creation_widget.update_stats('testing 123 test ! :)')
    assert password_line_creation_widget.progressbar.value() == 4


def test_password_creation_widget_blank(password_line_creation_widget):
    password_line_creation_widget.update_stats('')
    assert password_line_creation_widget.progressbar.value() == 0
