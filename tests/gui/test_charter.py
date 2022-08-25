# -*- coding: utf-8 -*-

from socket import timeout
from time import sleep

from unittest.mock import MagicMock

import pytest
# from qtpy.QtWidgets import QApplication
from twisted.python.filepath import FilePath

from qtpy.QtCore import Qt

from gridsync.core import Core


from gridsync.gui import Gui

from argparse import Namespace


def _test_basics(qtbot):
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


def _test_with_common_gui_addressing(qtbot):
    gui = Gui(MagicMock()) ## TBD: Do not use mocks
    window = gui.main_window
    window.show()
    qtbot.waitExposed(window)
    #qtbot.mouseClick(window.toolbar.combo_box, Qt.MouseButton.LeftButton)
    # window.toolbar.combo_box.setCurrentIndex(1)
    # window.toolbar.export_action_triggered.emit() # XXX: meh, we want to click instead of emitting signals.
    # qtbot.wait(9000)  # milliseconds, just so we can click around in the window a bit


def _test_recover_from_key(qtbot):
    gui = Gui(MagicMock()) # TBD: Do not use mocks
    gui.main_window.show_welcome_dialog()
    wd = gui.main_window.welcome_dialog
    qtbot.addWidget(wd)
    qtbot.mouseClick(wd.restore_link, Qt.MouseButton.LeftButton)

    ### XXX How to type some text into the file chooser dialoge
    ### without changing the gridsync source code?
    
    qtbot.wait(9000)  # milliseconds, just so we can click around in the window a bit



def test_start_welcomescreen(qtbot, qt_reactor):
    core = Core(Namespace(debug = False))
    assert core.gui.welcome_dialog is not None
    with qtbot.waitActive(core.gui.welcome_dialog):
        core.start_async(qt_reactor)
