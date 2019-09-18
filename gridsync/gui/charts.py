# -*- coding: utf-8 -*-

from PyQt5.QtChart import QChart, QChartView, QPieSeries
from PyQt5.QtCore import QMargins, Qt
from PyQt5.QtGui import QPainter, QPen


class ZKAPChart(QChart):
    def __init__(self):
        super().__init__()

        series = QPieSeries()
        series.setPieSize(0.9)
        series.setHoleSize(0.6)
        series.append('', 123456)
        series.append('', 500000)

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
                round(self.slice_available.value())
            )
        )


class ZKAPChartView(QChartView):
    def __init__(self):
        super().__init__()
        self.chart = ZKAPChart()
        self.setMaximumSize(26, 26)
        self.setChart(self.chart)
        self.setRenderHint(QPainter.Antialiasing)
