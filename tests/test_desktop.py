# -*- coding: utf-8 -*-

import pytest

from gridsync.desktop import (
    get_clipboard_modes, get_clipboard_text, set_clipboard_text)


def test_get_clipboard_modes():
    assert len(get_clipboard_modes()) >= 1


@pytest.mark.skipif(
    'CI' in os.environ, reason="Fails on some headless environments")
def test_clipboard_text():
    set_clipboard_text('test')
    assert get_clipboard_text() == 'test'
