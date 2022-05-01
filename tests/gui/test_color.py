# -*- coding: utf-8 -*-

import pytest
from qtpy.QtGui import QColor

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
