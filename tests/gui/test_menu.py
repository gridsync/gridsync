from unittest.mock import Mock

from gridsync.gui.menu import Menu


def test_about_action_trigger_shows_about_msg() -> None:
    menu = Menu(Mock())
    menu.about_action.trigger()
    assert menu.about_msg.isVisible() is True
