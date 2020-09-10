# -*- coding: utf-8 -*-

from PyQt5.QtChart import (
    QBarSet,
    QChart,
    QChartView,
    QHorizontalPercentBarSeries,
    QPieSeries,
)
from PyQt5.QtCore import QMargins, Qt
from PyQt5.QtGui import QColor, QPainter, QPalette, QPen

from gridsync.gui.color import is_dark

COLOR_USED = "#D42020"
COLOR_COST = "#EE9A1D"
COLOR_AVAILABLE = "#29A529"


class ZKAPPieChart(QChart):
    def __init__(self):
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

    def update_tooltip(self):
        self.setToolTip(
            "ZKAPs used: {}\n"
            "ZKAPs available: {}\n\n"
            "Last purchase: 2019-06-20 12:34:56".format(
                round(self.slice_used.value()),
                round(self.slice_available.value()),
            )
        )


class ZKAPBarChart(QChart):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self.unit_name = self.gateway.zkap_name_abbrev

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
        # series.append(self.set_cost)
        series.append(self.set_available)
        series.append(self.set_expected)

        self.addSeries(series)
        self.setAnimationOptions(QChart.SeriesAnimations)
        self.setBackgroundVisible(False)

        self.layout().setContentsMargins(0, 0, 0, 0)
        legend = self.legend()
        palette = self.palette()
        if is_dark(palette.color(QPalette.Background)):
            # The legend label text does not seem to be dark mode-aware
            # and will appear dark grey with macOS dark mode enabled,
            # making the labels illegible. This may be a bug with
            # PyQtChart. In any case, override it here..
            legend.setLabelColor(palette.color(QPalette.Text))
        legend.setAlignment(Qt.AlignBottom)
        legend.markers(series)[-1].setVisible(False)  # Hide set_expected

        self.update(10, 30, 40)  # XXX

    def update(self, used: int = 0, cost: int = 0, available: int = 0) -> None:
        self.set_used.replace(0, used)
        self.set_used.setLabel(f"{self.unit_name}s used ({used})")
        self.set_cost.replace(0, cost)
        self.set_cost.setLabel(f"Monthly {self.unit_name} cost ({cost})")
        self.set_available.replace(0, available)
        self.set_available.setLabel(
            f"{self.unit_name}s available ({available})"
        )
        total = used + available
        batch_size = self.gateway.zkap_batch_size
        if total <= batch_size:
            self.set_expected.replace(0, batch_size - total)
        else:
            self.set_expected.replace(0, 0)
        self.setToolTip("")  # XXX


class ZKAPCompactPieChartView(QChartView):
    def __init__(self):
        super().__init__()
        self.chart = ZKAPPieChart()
        self.setMaximumSize(26, 26)
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)


class ZKAPBarChartView(QChartView):
    def __init__(self, gateway):
        super().__init__()
        self.chart = ZKAPBarChart(gateway)
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)
