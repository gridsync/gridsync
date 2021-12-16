"""
pytest configuration for GridSync's GUI tests.
"""

from unittest.mock import MagicMock

import pytest
from PyQt5.QtWidgets import QApplication

from gridsync.gui import Gui

# Without this, QWidget() aborts the process with "QWidget: Must construct a
# QApplication before a QWidget".
app = QApplication([])


@pytest.fixture
def gui():
    return Gui(MagicMock())
