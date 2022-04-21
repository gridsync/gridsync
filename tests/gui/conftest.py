"""
pytest configuration for GridSync's GUI tests.
"""

from unittest.mock import MagicMock

import pytest
from qtpy.QtWidgets import QApplication
from twisted.python.filepath import FilePath

from gridsync.gui import Gui
from gridsync.preferences import Preferences

# Without this, QWidget() aborts the process with "QWidget: Must construct a
# QApplication before a QWidget".
app = QApplication([])


@pytest.fixture
def preferences_config_file(tmpdir_factory) -> FilePath:
    """
    The value of this fixture is a path suitable for use as a preferences
    configuration file.  It does not exist initially.
    """
    return FilePath(str(tmpdir_factory.mktemp("config"))).child(
        "preferences.ini"
    )


@pytest.fixture
def preferences(preferences_config_file: str) -> Preferences:
    """
    The value of this fixture is a preferences object which tests can set
    preferences in and get preferences from.
    """
    return Preferences(preferences_config_file)


@pytest.fixture
def gui(preferences: Preferences) -> Gui:
    """
    The value of this fixture is a GUI object which tests can add widgets to
    and do other GUI-y things to.
    """
    return Gui(MagicMock(), preferences=preferences)
