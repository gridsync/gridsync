# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Union

from humanize import naturaldelta
from qtpy.QtCharts import (
    QBarSet,
    QChart,
    QChartView,
    QHorizontalPercentBarSeries,
    QPieSeries,
)
from qtpy.QtCore import QMargins, Qt
from qtpy.QtGui import QColor, QPainter, QPalette, QPen

from gridsync.gui.color import is_dark
from gridsync.gui.font import Font

COLOR_USED = "#D42020"
COLOR_COST = "#EE9A1D"
COLOR_AVAILABLE = "#29A529"

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class ZKAPPieChart(QChart):
    def __init__(self) -> None:
        super().__init__()

        series = QPieSeries()
        series.setPieSize(0.9)
        series.setHoleSize(0.6)
        series.append("", 123456)
        series.append("", 500000)

        self.slice_used = series.slices()[0]
        self.slice_used.setPen(QPen(Qt.red, 0))
        self.slice_used.setBrush(Qt.red)

        self.slice_available = series.slices()[1]
        self.slice_available.setPen(QPen(Qt.darkGreen, 0))
        self.slice_available.setBrush(Qt.darkGreen)

        self.addSeries(series)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.legend().hide()
        self.setBackgroundVisible(False)
        self.setMargins(QMargins(0, 0, 0, 0))

        self.update_tooltip()

    def update_tooltip(self) -> None:
        self.setToolTip(
            "ZKAPs used: {}\n"
            "ZKAPs available: {}\n\n"
            "Last purchase: 2019-06-20 12:34:56".format(
                round(self.slice_used.value()),
                round(self.slice_available.value()),
            )
        )


class ZKAPBarChart(QChart):
    def __init__(self, gateway: Tahoe) -> None:
        super().__init__()
        self.gateway = gateway

        self.unit_multiplier = gateway.zkapauthorizer.zkap_unit_multiplier
        self.unit_name = gateway.zkapauthorizer.zkap_unit_name

        self.set_used = QBarSet("Used")
        # color_used = QColor("#1F9FDE")
        color_used = QColor(
            self.gateway.settings.get("zkap_color_used", COLOR_USED)
        )
        self.set_used.setPen(QPen(color_used, 0))
        self.set_used.setBrush(color_used)
        self.set_used.insert(0, 0)

        self.set_cost = QBarSet("Monthly cost")
        color_cost = QColor(
            self.gateway.settings.get("zkap_color_cost", COLOR_COST)
        )
        self.set_cost.setPen(QPen(color_cost, 0))
        self.set_cost.setBrush(color_cost)
        self.set_cost.insert(0, 0)

        self.set_available = QBarSet("Available")
        color_available = QColor(
            self.gateway.settings.get("zkap_color_available", COLOR_AVAILABLE)
        )
        self.set_available.setPen(QPen(color_available, 0))
        self.set_available.setBrush(color_available)
        self.set_available.insert(0, 0)

        self.set_expected = QBarSet("")
        color_expected = QColor("Light Grey")
        self.set_expected.setPen(QPen(color_expected, 0))
        self.set_expected.setBrush(color_expected)
        self.set_expected.insert(0, 0)

        series = QHorizontalPercentBarSeries()
        series.append(self.set_used)
        series.append(self.set_cost)
        series.append(self.set_available)
        series.append(self.set_expected)

        self.addSeries(series)
        try:
            self.setAnimationOptions(QChart.SeriesAnimations)
        except AttributeError:  # Moved(?) in (Py)Qt6
            self.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.setBackgroundVisible(False)

        self.layout().setContentsMargins(0, 0, 0, 0)
        legend = self.legend()
        palette = self.palette()
        if is_dark(palette.color(QPalette.Window)):
            # The legend label text does not seem to be dark mode-aware
            # and will appear dark grey with macOS dark mode enabled,
            # making the labels illegible. This may be a bug with
            # PyQtChart. In any case, override it here..
            legend.setLabelColor(palette.color(QPalette.Text))
        legend.setAlignment(Qt.AlignBottom)
        legend.setShowToolTips(True)
        legend.setFont(Font(9))
        legend_layout = legend.layout()
        _, top, _, bottom = legend_layout.getContentsMargins()
        legend_layout.setContentsMargins(0, top, 0, bottom)
        legend.markers(series)[-1].setVisible(False)  # Hide set_expected

        self.update_chart(10, 30, 40)  # XXX

    def _convert(self, value: int) -> Union[int, float]:
        if self.unit_multiplier == 1:
            return value
        if value < 10:
            return round(value * self.unit_multiplier, 3)
        return round(value * self.unit_multiplier, 2)

    def update_chart(
        self, used: int = 0, cost: int = 0, available: int = 0, period: int = 0
    ) -> None:
        self.set_used.replace(0, used)
        self.set_used.setLabel(
            f"{self.unit_name}s used ({self._convert(used)})"
        )
        self.set_cost.replace(0, cost)
        if period == 2678400:  # 31 days
            self.set_cost.setLabel(
                f"Expected 31 day cost ({self._convert(cost)})"
            )
        elif period:
            h = naturaldelta(dt.timedelta(seconds=period))
            self.set_cost.setLabel(
                f"Expected cost for {h} ({self._convert(cost)})"
            )
        else:
            self.set_cost.setLabel(f"Expected cost ({self._convert(used)})")
        self.set_available.replace(0, available)
        self.set_available.setLabel(
            f"{self.unit_name}s available ({self._convert(available)})"
        )
        total = used + available
        batch_size = self.gateway.zkapauthorizer.zkap_batch_size
        if total <= batch_size:
            self.set_expected.replace(0, batch_size - total)
        else:
            self.set_expected.replace(0, 0)
        self.setToolTip("")  # XXX


class ZKAPCompactPieChartView(QChartView):
    def __init__(self) -> None:
        super().__init__()
        self.setMaximumSize(26, 26)
        self.setChart(ZKAPPieChart())
        self.setRenderHint(QPainter.Antialiasing)


class ZKAPBarChartView(QChartView):
    def __init__(self, gateway: Tahoe) -> None:
        super().__init__()
        self.setChart(ZKAPBarChart(gateway))
        self.setRenderHint(QPainter.Antialiasing)
