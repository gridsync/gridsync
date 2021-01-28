# -*- coding: utf-8 -*-

import logging
import webbrowser
from datetime import datetime, timedelta

from humanize import naturalsize
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtGui import QFontDatabase, QIcon, QPainter
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)
from twisted.internet.defer import inlineCallbacks

from gridsync import APP_NAME, resource
from gridsync.desktop import get_browser_name
from gridsync.gui.charts import ZKAPBarChartView
from gridsync.gui.font import Font
from gridsync.voucher import generate_voucher, is_valid


class VoucherCodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setMinimumWidth(400)

        self.label = QLabel("Enter voucher code:")
        self.label.setFont(Font(14))
        self.label.setStyleSheet("color: gray")

        self.lineedit = QLineEdit(self)
        # self.lineedit.setFont(Font(14))
        # font = Font(14)
        # font.setStyleHint(QFont.Monospace)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(14)
        self.lineedit.setFont(font)
        mask = ">NNNN-NNNN-NNNN-NNNN"
        self.lineedit.setInputMask(mask)
        self.lineedit.setFixedWidth(
            self.lineedit.fontMetrics().boundingRect(mask).width() + 10
        )
        margins = self.lineedit.textMargins()
        margins.setLeft(margins.left() + 4)  # XXX
        self.lineedit.setTextMargins(margins)
        self.lineedit.returnPressed.connect(self.on_return_pressed)
        self.lineedit.textEdited.connect(
            lambda _: self.error_message_label.setText("")
        )
        # self.lineedit.setEchoMode(QLineEdit.Password)
        # self.action = QAction(QIcon(resource("eye.png")), "Toggle visibility")
        # self.action.triggered.connect(self.toggle_visibility)
        # self.lineedit.addAction(self.action, QLineEdit.TrailingPosition)

        self.error_message_label = QLabel()
        self.error_message_label.setAlignment(Qt.AlignCenter)
        self.error_message_label.setFont(Font(10))
        self.error_message_label.setStyleSheet("color: red")

        layout = QGridLayout(self)
        layout.addWidget(self.label, 1, 1)
        layout.addWidget(self.lineedit, 2, 1)
        layout.addWidget(self.error_message_label, 3, 1)

    def on_return_pressed(self):
        text = self.lineedit.text().replace("-", "")
        if is_valid(text):
            self.accept()
        else:
            self.error_message_label.setText("Invalid code; please try again")

    @staticmethod
    def get_voucher(parent=None):
        dialog = VoucherCodeDialog(parent)
        result = dialog.exec_()
        return (
            generate_voucher(dialog.lineedit.text().replace("-", "").encode()),
            result,
        )


class ZKAPInfoPane(QWidget):
    def __init__(self, gateway, gui):
        super().__init__()
        self.gateway = gateway
        self.gui = gui

        self._zkaps_used: int = 0
        self._zkaps_cost: int = 0
        self._zkaps_remaining: int = 0
        self._zkaps_total: int = 0
        self._zkaps_period: int = 0
        self._last_purchase_date: str = "Not available"
        self._expiry_date: str = "Not available"
        self._amount_stored: str = "Not available"
        self.voucher_dialog = None

        self.groupbox = QGroupBox()

        self.title = QLabel("Storage-time")
        font = Font(11)
        font.setBold(True)
        self.title.setFont(font)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.hide()

        self.explainer_label = QLabel(
            f"The {APP_NAME} app will gradually consume your storage-time to "
            "keep your data saved."
        )
        font = Font(10)
        font.setItalic(True)
        self.explainer_label.setFont(font)
        self.explainer_label.setAlignment(Qt.AlignCenter)
        self.explainer_label.hide()

        self.zkaps_required_label = QLabel(
            "You currently have 0 GB-months available.\n\nIn order to store "
            f"data with {gateway.name}, you will need to buy storage-time."
        )
        self.zkaps_required_label.setAlignment(Qt.AlignCenter)
        self.zkaps_required_label.setWordWrap(True)

        self.chart_view = ZKAPBarChartView(self.gateway)
        self.chart_view.setFixedHeight(128)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.hide()

        self.info_label = QLabel()
        self.info_label.setFont(Font(10))

        browser = get_browser_name()
        self.button = QPushButton(f"Buy storage-time in {browser} ")
        self.button.setStyleSheet("background: green; color: white")
        self.button.setIcon(QIcon(resource("globe-white.png")))
        self.button.setLayoutDirection(Qt.RightToLeft)
        self.button.clicked.connect(self.on_button_clicked)
        self.button.setFixedSize(240, 32)

        self.voucher_link = QLabel("<a href>I have a voucher code</a>")
        self.voucher_link.linkActivated.connect(self.on_voucher_link_clicked)

        layout = QGridLayout()
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 10, 0)
        layout.addWidget(self.title, 20, 0)
        layout.addWidget(self.explainer_label, 30, 0)
        layout.addWidget(self.zkaps_required_label, 40, 0)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 50, 0)
        layout.addWidget(self.chart_view, 60, 0)
        layout.addWidget(self.info_label, 70, 0, Qt.AlignCenter)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 80, 0)
        layout.addWidget(self.button, 90, 0, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.voucher_link, 100, 0, 1, 1, Qt.AlignCenter)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 110, 0)

        self.groupbox.setLayout(layout)

        main_layout = QGridLayout(self)
        main_layout.addWidget(self.groupbox)

        self.gateway.monitor.zkaps_redeemed.connect(self.on_zkaps_redeemed)
        self.gateway.monitor.zkaps_updated.connect(self.on_zkaps_updated)
        # self.gateway.monitor.zkaps_renewal_cost_updated.connect(
        #    self.on_zkaps_renewal_cost_updated
        # )
        self.gateway.monitor.zkaps_price_updated.connect(
            self.on_zkaps_renewal_cost_updated
        )
        self.gateway.monitor.days_remaining_updated.connect(
            self.on_days_remaining_updated
        )
        self.gateway.monitor.total_folders_size_updated.connect(
            self.on_total_folders_size_updated
        )
        self.gateway.monitor.low_zkaps_warning.connect(
            self.on_low_zkaps_warning
        )

    @inlineCallbacks
    def _open_zkap_payment_url(self):  # XXX/TODO: Handle errors
        voucher = generate_voucher()  # TODO: Cache to disk
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

    @Slot()
    def on_voucher_link_clicked(self):
        voucher, ok = VoucherCodeDialog.get_voucher()
        if ok:
            self.gateway.add_voucher(voucher)

    def _update_info_label(self):
        self.info_label.setText(
            f"Last purchase: {self._last_purchase_date} ("
            f"{self.chart_view.chart._convert(self.gateway.zkap_batch_size)} "
            f"{self.gateway.zkap_unit_name_abbrev}s)     "
            f"Expected expiry: {self._expiry_date}"
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
            self.title.show()
            self.explainer_label.show()
            self.chart_view.show()
        self.chart_view.chart.update(
            self._zkaps_used,
            self._zkaps_cost,
            self._zkaps_remaining,
            self._zkaps_period,
        )
        self.gui.main_window.maybe_enable_actions()

    @Slot(int, int)
    def on_zkaps_updated(self, used, remaining):
        self._zkaps_used = used
        self._zkaps_remaining = remaining
        self._zkaps_total = used + remaining
        self._update_chart()

    @Slot(int, int)
    def on_zkaps_renewal_cost_updated(self, cost, period):
        self._zkaps_cost = cost
        self._zkaps_period = period
        self._update_chart()

    @Slot(int)
    def on_days_remaining_updated(self, days: int) -> None:
        self._expiry_date = datetime.strftime(
            datetime.strptime(
                datetime.isoformat(datetime.now() + timedelta(days=days)),
                "%Y-%m-%dT%H:%M:%S.%f",
            ),
            "%d %b %Y",
        )
        self._update_info_label()

    @Slot(object)
    def on_total_folders_size_updated(self, size: int) -> None:
        self._amount_stored = naturalsize(size)
        self._update_info_label()

    def on_low_zkaps_warning(self) -> None:
        self.gui.show_message(
            "Low storage-time",
            "Your storage-time is running low. Please buy more storage-time "
            "to prevent data-loss.",
        )
        self.gui.main_window.show_zkap_view()
