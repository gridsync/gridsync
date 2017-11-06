# -*- coding: utf-8 -*-

import os

import pytest
from PyQt5.QtWidgets import QMessageBox


@pytest.mark.skipif('CI' in os.environ, reason="Fails on Travis-CI/AppVeyor")
def test_pyqt59_shortcut_key_press_regression(qtbot):
    msg = QMessageBox()
    qtbot.add_widget(msg)
    with qtbot.wait_signal(msg.finished):
        msg.show()
        qtbot.waitActive(msg)
        qtbot.keyPress(msg, 'O')  # Shortcut to activate default "OK" button
