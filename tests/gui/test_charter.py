# -*- coding: utf-8 -*-

from time import sleep

from unittest.mock import MagicMock

import pytest
from qtpy.QtWidgets import QApplication
from twisted.python.filepath import FilePath

from qtpy.QtCore import Qt

from gridsync.gui import Gui


def test_with_common_gui_addressing(qtbot):
    gui = Gui(MagicMock())
    window = gui.main_window
    window.show()
    qtbot.waitExposed(window)
    window.toolbar.folder_action.setEnabled(True)
    qtbot.mouseClick(window.toolbar.folder_button, Qt.MouseButton.LeftButton)
    window.toolbar.export_action_triggered.emit() # XXX: meh, we want to click instead of emitting signals.
    qtbot.wait(5000)


def test_basics(qtbot):
    """
    Basic test that works more like a sanity check to ensure we are setting up a QApplication
    properly and are able to display a simple event_recorder.
    """
    from pytestqt.qt_compat import qt_api
    assert qt_api.QtWidgets.QApplication.instance() is not None
    widget = qt_api.QtWidgets.QWidget()
    qtbot.addWidget(widget)
    widget.setWindowTitle("W1")
    widget.show()

    assert widget.isVisible()
    assert widget.windowTitle() == "W1"

