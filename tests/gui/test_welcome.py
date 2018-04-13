# -*- coding: utf-8 -*-

from gridsync.gui.welcome import WelcomeDialog


def test_init_welcome_dialog():
    welcome_dialog = WelcomeDialog(None)
    assert welcome_dialog
