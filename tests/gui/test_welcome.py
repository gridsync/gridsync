# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from gridsync.gui.welcome import WelcomeDialog


def test_init_welcome_dialog():
    welcome_dialog = WelcomeDialog(MagicMock())
    assert welcome_dialog
