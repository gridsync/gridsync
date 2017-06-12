# -*- coding: utf-8 -*-

from gridsync.gui.setup import SetupForm


def test_init_invite_form():
    setup_form = SetupForm(None)
    assert setup_form
