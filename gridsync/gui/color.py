# -*- coding: utf-8 -*-

from PyQt5.QtGui import QColor


class BlendedColor(QColor):
    def __init__(self, color_a, color_b, pct_a=0.5):
        super().__init__()
        pct_b = 1.0 - pct_a
        self.setRgb(
            pct_a * color_a.red() + pct_b * color_b.red(),
            pct_a * color_a.green() + pct_b * color_b.green(),
            pct_a * color_a.blue() + pct_b * color_b.blue(),
            pct_a * color_a.alpha() + pct_b * color_b.alpha()
        )
