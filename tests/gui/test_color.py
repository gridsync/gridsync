# -*- coding: utf-8 -*-

from PyQt5.QtGui import QColor
import pytest

from gridsync.gui.color import is_dark


@pytest.mark.parametrize(
    "color,result",
    [
        (QColor("black"), True),
        (QColor("grey"), True),
        (QColor("white"), False),
    ],
)
def test_is_dark(color, result):
    assert is_dark(color) == result
