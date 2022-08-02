# -*- coding: utf-8 -*-

from time import sleep

from unittest.mock import MagicMock

import pytest
from qtpy.QtWidgets import QApplication
from twisted.python.filepath import FilePath

from qtpy.QtCore import Qt

from gridsync.gui import Gui
# from gridsync.gui import MainWindow

# Without this, QWidget() aborts the process with "QWidget: Must construct a
# QApplication before a QWidget".
#app = QApplication([])


#@pytest.fixture
#def gui(preferences: Preferences) -> Gui:
#    """
#    The value of this fixture is a GUI object which tests can add widgets to
#    and do other GUI-y things to.
#    """
#    return Gui(MagicMock(), preferences=preferences)

#def test_with_qtbot(qtbot):
#    #with qtbot.wait_signals([proc.started, proc.finished], timeout=10000, order='strict'):
#    window = Gui(MagicMock())
#    #qtbot.addWidget(window)
#    window.show()
#    qtbot.waitForWindowShown(window)
#    qtbot.mouseClick(window)

def test_with_common_gui_addressing(qtbot):
    gui = Gui(MagicMock())
    window = gui.main_window
    window.show()
    qtbot.waitExposed(window)
    window.toolbar.folder_action.setEnabled(True)
    qtbot.mouseClick(window.toolbar.folder_button, Qt.MouseButton.LeftButton)
    window.toolbar.export_action_triggered.emit() # XXX: meh, we want to click instead of emitting signals.
    qtbot.wait(5000)

def test_with_qtbot_mw(qtbot):
    #with qtbot.wait_signals([proc.started, proc.finished], timeout=10000, order='strict'):
    window = MainWindow(Gui(MagicMock()))
    #qtbot.addWidget(window)
    window.show()
    qtbot.waitForWindowShown(window)

def test_with_qtbot_mw(qtbot):
    #with qtbot.wait_signals([proc.started, proc.finished], timeout=10000, order='strict'):
    window = MainWindow(Gui(MagicMock()))
    #qtbot.addWidget(window)
    window.show()
    qtbot.waitForWindowShown(window)
    qtbot.mouseClick(window.add_folder_icon)


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

