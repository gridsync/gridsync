# -*- coding: utf-8 -*-

import os
import sys

import pytest
from PyQt5.QtCore import PYQT_VERSION_STR
from PyQt5.QtWidgets import QMessageBox


@pytest.mark.skipif(
    PYQT_VERSION_STR == "5.7.1" and sys.platform == "linux",
    reason="Segmentation fault observed on Debian 9",
)
@pytest.mark.skipif("CI" in os.environ, reason="Fails on Travis-CI/AppVeyor")
@pytest.mark.xfail(PYQT_VERSION_STR == "5.9", reason="Fails on PyQt 5.9")
# https://bugreports.qt.io/browse/QTBUG-61197
# https://bugreports.qt.io/browse/QTBUG-54119
def test_pyqt59_shortcut_key_press_regression(qtbot):
    msg = QMessageBox()
    qtbot.add_widget(msg)
    with qtbot.wait_signal(msg.finished):
        msg.show()
        qtbot.waitActive(msg)
        qtbot.keyPress(msg, "O")  # Shortcut to activate default "OK" button
