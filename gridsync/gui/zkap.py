# -*- coding: utf-8 -*-

import logging
import webbrowser
from datetime import datetime

from humanize import naturalsize
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QIcon, QPainter
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)
from twisted.internet.defer import inlineCallbacks

from gridsync import resource
from gridsync.desktop import get_browser_name
from gridsync.gui.charts import ZKAPBarChartView
from gridsync.gui.font import Font


class ZKAPInfoPane(QWidget):
    def __init__(self, gateway, gui):
        super().__init__()
        self.gateway = gateway
        self.gui = gui

        self._zkaps_used: int = 0
        self._zkaps_cost: int = 0
        self._zkaps_remaining: int = 0
        self._zkaps_total: int = 0
        self._last_purchase_date: str = "Not available"
        self._amount_stored: str = "Not available"

        self.groupbox = QGroupBox()

        title = QLabel(
            f"{gateway.zkap_name_plural} ({gateway.zkap_name_abbrev}s)"
        )
        font = Font(11)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)

        self.explainer_label = QLabel(
            f"{gateway.zkap_name_abbrev}s will be spent automatically on a "
            "monthly basis to keep your data stored."
        )
        font = Font(10)
        font.setItalic(True)
        self.explainer_label.setFont(font)
        self.explainer_label.setAlignment(Qt.AlignCenter)
        self.explainer_label.hide()

        self.zkaps_required_label = QLabel(
            f"<br><i>{gateway.zkap_name_plural}</i> -- or "
            f"<i>{gateway.zkap_name_abbrev}s</i> -- are required to store "
            f"data on the {gateway.name} grid. You currently have <b>0</b> "
            f"{gateway.zkap_name_abbrev}s. In order to continue, you will "
            f"need to purchase {gateway.zkap_name_abbrev}s."
        )
        self.zkaps_required_label.setWordWrap(True)

        self.chart_view = ZKAPBarChartView(self.gateway)
        self.chart_view.setFixedHeight(128)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.hide()

        self.info_label = QLabel()
        self.info_label.setFont(Font(10))

        browser = get_browser_name()
        self.button = QPushButton(
            f"Buy {gateway.zkap_name_abbrev}s in {browser} "
        )
        self.button.setStyleSheet("background: green; color: white")
        self.button.setIcon(QIcon(resource("globe-white.png")))
        self.button.setLayoutDirection(Qt.RightToLeft)
        self.button.clicked.connect(self.on_button_clicked)
        self.button.setFixedSize(240, 32)

        layout = QGridLayout()
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 10, 0)
        layout.addWidget(title, 20, 0)
        layout.addWidget(self.explainer_label, 30, 0)
        layout.addWidget(self.zkaps_required_label, 40, 0)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 50, 0)
        layout.addWidget(self.chart_view, 60, 0)
        layout.addWidget(self.info_label, 70, 0, Qt.AlignCenter)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 80, 0)
        layout.addWidget(self.button, 90, 0, 1, 1, Qt.AlignCenter)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 110, 0)

        self.groupbox.setLayout(layout)

        main_layout = QGridLayout(self)
        main_layout.addWidget(self.groupbox)

        self.gateway.monitor.zkaps_redeemed.connect(self.on_zkaps_redeemed)
        self.gateway.monitor.zkaps_updated.connect(self.on_zkaps_updated)
        self.gateway.monitor.zkaps_renewal_cost_updated.connect(
            self.on_zkaps_renewal_cost_updated
        )
        # self.gateway.monitor.days_remaining_updated.connect(
        #    self.on_days_remaining_updated
        # )
        self.gateway.monitor.total_folders_size_updated.connect(
            self.on_total_folders_size_updated
        )
        self.gateway.monitor.low_zkaps_warning.connect(
            self.on_low_zkaps_warning
        )

    @inlineCallbacks
    def _open_zkap_payment_url(self):  # XXX/TODO: Handle errors
        voucher = self.gateway.generate_voucher()  # TODO: Cache to disk
        payment_url = self.gateway.zkap_payment_url(voucher)
        logging.debug("Opening payment URL %s ...", payment_url)
        if webbrowser.open(payment_url):
            logging.debug("Browser successfully launched")
        else:  # XXX/TODO: Raise a user-facing error
            logging.error("Error launching browser")
        yield self.gateway.add_voucher(voucher)

    @Slot()
    def on_button_clicked(self):
        self._open_zkap_payment_url()

    def _update_info_label(self):
        self.info_label.setText(
            f"Last purchase: {self._last_purchase_date} "
            f"({self.gateway.zkap_batch_size} "
            f"{self.gateway.zkap_name_abbrev}s)     "
            f"Amount stored: {self._amount_stored}"
        )

    @Slot(str)
    def on_zkaps_redeemed(self, timestamp):
        self._last_purchase_date = datetime.strftime(
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f"), "%d %b %Y"
        )
        self.zkaps_required_label.hide()
        self.explainer_label.show()
        self.chart_view.show()
        self._update_info_label()

    def _update_chart(self):
        if self._zkaps_remaining:
            self.zkaps_required_label.hide()
            self.explainer_label.show()
            self.chart_view.show()
        self.chart_view.chart.update(
            self._zkaps_used, self._zkaps_cost, self._zkaps_remaining
        )
        self.gui.main_window.maybe_enable_actions()

    @Slot(int, int)
    def on_zkaps_updated(self, used, remaining):
        self._zkaps_used = used
        self._zkaps_remaining = remaining
        self._zkaps_total = used + remaining
        self._update_chart()

    @Slot(int)
    def on_zkaps_renewal_cost_updated(self, cost):
        self._zkaps_cost = cost
        self._update_chart()

    # @Slot(int)
    # def on_days_remaining_updated(self, days):
    #    delta = timedelta(days=days)
    #    try:
    #        self.expiration_field.setText(naturaldelta(delta))
    #    except OverflowError:
    #        # Raises if days >= datetime.today().toordinal()
    #        self.expiration_field.setText("Several years")
    #    date = datetime.isoformat(datetime.now() + delta).split("T")[0]
    #    self.expiration_field.setToolTip(f"Expires: {date}")

    @Slot(object)
    def on_total_folders_size_updated(self, size: int) -> None:
        self._amount_stored = naturalsize(size)
        self._update_info_label()

    def on_low_zkaps_warning(self) -> None:
        self.gui.show_message(
            f"Warning: Low {self.gateway.zkap_name_abbrev}s",
            f"The number of {self.gateway.zkap_name_plural} available is "
            f"low. Please purchase more {self.gateway.zkap_name_abbrev}s "
            "to prevent data-loss.",
        )
        self.gui.main_window.show_zkap_view()
