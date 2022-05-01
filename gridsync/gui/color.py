# -*- coding: utf-8 -*-

from qtpy.QtGui import QColor


class BlendedColor(QColor):
    def __init__(self, color_a, color_b, pct_a=0.5):
        super().__init__()
        pct_b = 1.0 - pct_a
        self.setRgb(
            int(pct_a * color_a.red() + pct_b * color_b.red()),
            int(pct_a * color_a.green() + pct_b * color_b.green()),
            int(pct_a * color_a.blue() + pct_b * color_b.blue()),
            int(pct_a * color_a.alpha() + pct_b * color_b.alpha()),
        )


def is_dark(color: QColor) -> bool:
    r, g, b, _ = color.getRgb()
    return (r + g + b) <= (128 * 3)  # XXX
