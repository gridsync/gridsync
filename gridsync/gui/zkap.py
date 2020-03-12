# -*- coding: utf-8 -*-

import logging
import webbrowser

from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)
from twisted.internet.defer import inlineCallbacks

from gridsync.gui.charts import ZKAPBarChartView
from gridsync.gui.font import Font


class ZKAPInfoPane(QWidget):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self._zkaps_used: int = 0
        self._zkaps_cost: int = 0
        self._zkaps_remaining: int = 0

        self.groupbox = QGroupBox()

        title = QLabel(
            f"{gateway.zkap_name_plural} ({gateway.zkap_name_abbrev}s)"
        )
        font = Font(11)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)

        subtext = QLabel(f"1 {gateway.zkap_name_abbrev} = 1 MB for 30 days")
        font = Font(10)
        font.setItalic(True)
        subtext.setFont(font)
        subtext.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel(
            f"<br><i><a href>{gateway.zkap_name_plural}</a></i> -- or "
            f"<i>{gateway.zkap_name_abbrev}s</i> -- are required to store "
            f"data on the {gateway.name} grid. You currently have <b>0</b> "
            f"{gateway.zkap_name_abbrev}s. <p>In order to continue, you will "
            f"need to purchase {gateway.zkap_name_abbrev}s, or generate them "
            "by redeeming a voucher code."
        )
        self.text_label.setWordWrap(True)

        self.spacer = QSpacerItem(0, 0, 0, QSizePolicy.Expanding)

        self.chart_view = ZKAPBarChartView()
        self.chart_view.setFixedHeight(128)
        self.chart_view.setRenderHint(QPainter.Antialiasing)

        form_layout = QFormLayout()

        self.refill_label = QLabel("Last Refill")
        self.refill_field = QLabel("Not available")
        self.refill_field.setAlignment(Qt.AlignRight)

        self.usage_label = QLabel(
            f"{gateway.zkap_name_abbrev} usage (since last refill)"
        )
        self.usage_field = QLabel("Not available")
        self.usage_field.setAlignment(Qt.AlignRight)

        self.expiration_label = QLabel("Next Expiration (at current usage)")
        self.expiration_field = QLabel("Not available")
        self.expiration_field.setAlignment(Qt.AlignRight)

        self.stored_label = QLabel("Total Current Amount Stored")
        self.stored_field = QLabel("Not available")
        self.stored_field.setAlignment(Qt.AlignRight)

        form_layout.addRow(self.refill_label, self.refill_field)
        form_layout.addRow(self.usage_label, self.usage_field)
        form_layout.addRow(self.expiration_label, self.expiration_field)
        form_layout.addRow(self.stored_label, self.stored_field)

        self.button = QPushButton(f"Purchase {gateway.zkap_name_abbrev}s")
        self.button.setStyleSheet("background: green; color: white")
        self.button.clicked.connect(self.on_button_clicked)
        # button.setFixedSize(150, 40)
        self.button.setFixedSize(180, 30)

        self.voucher_link = QLabel("<a href>I have a voucher code</a>")

        self.pending_label = QLabel("")
        self.pending_label.setWordWrap(True)
        self.pending_label.hide()

        layout = QGridLayout()
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 10, 0)
        layout.addWidget(title, 20, 0)
        # layout.addWidget(subtext, 30, 0)
        layout.addWidget(self.text_label, 40, 0)
        # layout.addWidget(QLabel(" "), 50, 0)
        layout.addItem(self.spacer, 60, 0)
        layout.addLayout(form_layout, 70, 0)
        layout.addWidget(self.chart_view, 80, 0)
        layout.addWidget(self.button, 90, 0, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.pending_label, 100, 0, 1, 1, Qt.AlignCenter)
        # layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 100, 0)
        layout.addWidget(self.voucher_link, 120, 0, 1, 1, Qt.AlignCenter)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 999, 0)

        self.groupbox.setLayout(layout)

        main_layout = QGridLayout(self)
        main_layout.addWidget(self.groupbox)

        self.gateway.monitor.zkaps_redeemed_time.connect(
            self.on_zkaps_redeemed_time
        )
        self.gateway.monitor.zkaps_updated.connect(self.on_zkaps_updated)
        self.gateway.monitor.zkaps_monthly_cost_updated.connect(
            self.on_zkaps_monthly_cost_updated
        )

        self.chart_view.hide()
        self._hide_table()

    def _show_table(self):
        self.refill_label.show()
        self.refill_field.show()
        self.usage_label.show()
        self.usage_field.show()
        self.expiration_label.show()
        self.expiration_field.show()
        self.stored_label.show()
        self.stored_field.show()

    def _hide_table(self):
        self.refill_label.hide()
        self.refill_field.hide()
        self.usage_label.hide()
        self.usage_field.hide()
        self.expiration_label.hide()
        self.expiration_field.hide()
        self.stored_label.hide()
        self.stored_field.hide()

    def _update_pending_label(self, payment_url=""):
        # self.pending_label.setText(
        #     f"A payment to {self.gateway.name} is still pending. To complete "
        #     f"payment please visit: <a href>{payment_url}</a><p><p>"
        #     "This page will update once payment has been successfully "
        #     "received and processed (this can take several minutes)."
        # )
        self.pending_label.setText(
             f"A payment to {self.gateway.name} is still pending. "
             "This page will update once payment has been successfully "
             "received and process (this can take several minutes)."
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
        self._update_pending_label(payment_url)
        self.pending_label.show()
        self.button.hide()
        self.voucher_link.hide()

    @Slot()
    def on_button_clicked(self):
        self._open_zkap_payment_url()

    @Slot(str)
    def on_zkaps_redeemed_time(self, timestamp):
        self.refill_field.setText(timestamp.split("T")[0])  # TODO: humanize
        self.text_label.hide()
        self._show_table()
        self.chart_view.show()

    def _update_chart(self):
        self.chart_view.chart.update(
            self._zkaps_used,
            self._zkaps_cost,
            self._zkaps_remaining,
        )

    @Slot(int, int)
    def on_zkaps_updated(self, remaining, total):
        self._zkaps_used = total - remaining
        self._zkaps_remaining = remaining
        self._update_chart()
        self.usage_field.setText(str(self._zkaps_used))

    @Slot(int)
    def on_zkaps_monthly_cost_updated(self, cost):
        self._zkaps_cost = cost
        self._update_chart()
