# -*- coding: utf-8 -*-

import pytest
from PyQt5.QtWidgets import QMessageBox


def test_pyqt59_shortcut_key_press_regression(qtbot):
    msg = QMessageBox()
    with qtbot.wait_signal(msg.finished):
        msg.show()
        qtbot.waitActive(msg)
        qtbot.keyPress(msg, 'O')  # Shortcut to activate default "OK" button 
