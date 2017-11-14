# -*- coding: utf-8 -*-

import pytest

from gridsync.gui.password import PasswordLineEdit, PasswordDialog


@pytest.fixture(scope='module')
def password_line_edit():
    widget = PasswordLineEdit()
    return widget


@pytest.fixture(scope='module')
def password_dialog():
    widget = PasswordDialog()
    return widget


def test_password_line_edit_toggle_visibility_on(password_line_edit):
    password_line_edit.action.triggered.emit()
    assert password_line_edit.echoMode() == PasswordLineEdit.Normal


def test_password_line_edit_toggle_visibility_off(password_line_edit):
    password_line_edit.action.triggered.emit()
    assert password_line_edit.echoMode() == PasswordLineEdit.Password


def test_password_dialog_very_weak(password_dialog):
    password_dialog.update_stats('test')
    assert password_dialog.progressbar.value() == 1


def test_password_dialog_weak(password_dialog):
    password_dialog.update_stats('test12345')
    assert password_dialog.progressbar.value() == 1


def test_password_dialog_alright(password_dialog):
    password_dialog.update_stats('testing 123 test')
    assert password_dialog.progressbar.value() == 2


def test_password_dialog_good(password_dialog):
    password_dialog.update_stats('testing 123 test !')
    assert password_dialog.progressbar.value() == 3


def test_password_dialog_excellent(password_dialog):
    password_dialog.update_stats('testing 123 test ! :)')
    assert password_dialog.progressbar.value() == 4


def test_password_dialog_blank(password_dialog):
    password_dialog.update_stats('')
    assert password_dialog.progressbar.value() == 0
