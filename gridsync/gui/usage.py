# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import traceback
import webbrowser
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

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
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync import APP_NAME, resource
from gridsync.desktop import get_browser_name
from gridsync.gui.charts import ZKAPBarChartView
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.voucher import VoucherCodeDialog
from gridsync.msg import error
from gridsync.types import TwistedDeferred

if TYPE_CHECKING:
    from gridsync.gui import Gui  # pylint: disable=cyclic-import
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


def make_explainer_label():
    explainer_label = QLabel(
        f"The {APP_NAME} app will gradually consume your storage-time to "
        "keep your data saved."
    )
    font = Font(10)
    font.setItalic(True)
    explainer_label.setFont(font)
    explainer_label.setAlignment(Qt.AlignCenter)
    explainer_label.hide()
    return explainer_label

def make_zkaps_required_label(is_commercial_grid):
    if is_commercial_grid:
        action = "buy storage-time"
    else:
        action = "add storage-time using a voucher code"
    zkaps_required_label = QLabel(
        "You currently have 0 GB-months available.\n\nIn order to store "
        f"data with {gateway.name}, you will need to {action}."
    )
    zkaps_required_label.setAlignment(Qt.AlignCenter)
    zkaps_required_label.setWordWrap(True)
    return zkaps_required_label

def make_chart_view(gateway):
    chart_view = ZKAPBarChartView(gateway)
    chart_view.setFixedHeight(128)
    chart_view.setRenderHint(QPainter.Antialiasing)
    chart_view.hide()
    return chart_view

def make_purchase_button(is_commercial_grid):
    if is_commercial_grid:
        browser = get_browser_name()
        button = QPushButton(f"Buy storage-time in {browser} ")
        button.setIcon(QIcon(resource("globe-white.png")))
        button.setLayoutDirection(Qt.RightToLeft)
    else:
        button = QPushButton("Use voucher code")
    button.setStyleSheet("background: green; color: white")
    button.setFixedSize(240, 32)
    return button

def make_voucher_link(is_commercial_grid):
    voucher_link = QLabel("<a href>I have a voucher code</a>")
    if not is_commercial_grid:
        voucher_link.hide()
    return voucher_link

def make_layout(
        title,
        explainer_label,
        zkaps_required_label,
        chart_view,
        info_label,
        button,
        voucher_link,
        status_label,
):
    layout = QGridLayout()
    layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 10, 0)
    layout.addWidget(title, 20, 0)
    layout.addWidget(explainer_label, 30, 0)
    layout.addWidget(zkaps_required_label, 40, 0)
    layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 50, 0)
    layout.addWidget(chart_view, 60, 0)
    layout.addWidget(info_label, 70, 0, Qt.AlignCenter)
    layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 80, 0)
    layout.addWidget(button, 90, 0, 1, 1, Qt.AlignCenter)
    layout.addWidget(voucher_link, 100, 0, 1, 1, Qt.AlignCenter)
    layout.addWidget(status_label, 110, 0, 1, 1, Qt.AlignCenter)
    layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 110, 0)
    return layout


class UsageView(QWidget):
    def __init__(self, gateway: Tahoe, gui: Gui) -> None:
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

        self.is_commercial_grid = bool(
            "zkap_payment_url_root" in gateway.settings
        )

        self.groupbox = QGroupBox()

        self.title = QLabel("Storage-time")
        font = Font(11)
        font.setBold(True)
        self.title.setFont(font)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.hide()

        self.explainer_label = make_explainer_label()
        self.zkaps_required_label = make_zkaps_required_label(self.is_commercial_grid)
        self.chart_view = make_chart_view(self.gateway)

        self.info_label = QLabel()
        self.info_label.setFont(Font(10))

        self.button = make_purchase_button()
        self.button.clicked.connect(self.on_button_clicked)

        self.voucher_link = make_voucher_link(self.is_commercial_grid)
        self.voucher_link.linkActivated.connect(self.on_voucher_link_clicked)

        self.status_label = QLabel(" ")
        self.status_label.setFont(Font(10))

        layout = make_layout(
            self.title,
            self.explainer_label,
            self.zkaps_required_label,
            self.chart_view,
            self.info_label,
            self.button,
            self.voucher_link,
            self.status_label,
        )
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
        self.gateway.magic_folder.monitor.total_folders_size_updated.connect(
            self.on_total_folders_size_updated
        )
        self.gateway.monitor.low_zkaps_warning.connect(
            self.on_low_zkaps_warning
        )

        self._reset_status()

    def _reset_status(self) -> None:
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color()
        ).name()
        self.status_label.setStyleSheet(f"color: {dimmer_grey}")
        self.status_label.setText(" ")

    @inlineCallbacks
    def add_voucher(self, voucher: str = "") -> TwistedDeferred[str]:
        self.status_label.setText("Creating voucher...")
        added = yield self.gateway.zkapauthorizer.add_voucher(voucher)
        self.status_label.setText("Verifying voucher...")
        data = yield self.gateway.zkapauthorizer.get_voucher(added)
        actual = data.get("number")
        if added != actual:
            raise ValueError(
                f'Voucher mismatch; the voucher "{added}" was added to '
                f'ZKAPAuthorizer but was stored as "{actual}"'
            )
        return added

    @staticmethod
    def _traceback(exc: Exception) -> str:
        return "".join(
            traceback.format_exception(
                etype=type(exc), value=exc, tb=exc.__traceback__
            )
        )

    @Slot()
    @inlineCallbacks
    def on_voucher_link_clicked(self) -> TwistedDeferred[None]:
        voucher, ok = VoucherCodeDialog.get_voucher()
        if not ok:
            return
        try:
            yield self.add_voucher(voucher)
        except Exception as exc:  # pylint: disable=broad-except
            self.status_label.setText("Error adding voucher")
            self.status_label.setStyleSheet("color: red")
            reactor.callLater(5, self._reset_status)  # type: ignore
            error(self, "Error adding voucher", str(exc), self._traceback(exc))
            return
        self.status_label.setText(
            "Voucher successfully added; token redemption should begin shortly"
        )
        reactor.callLater(10, self._reset_status)  # type: ignore

    @inlineCallbacks
    def _open_zkap_payment_url(self) -> TwistedDeferred[None]:
        try:
            voucher = yield self.add_voucher()
        except Exception as exc:  # pylint: disable=broad-except
            self.status_label.setText("Error adding voucher")
            self.status_label.setStyleSheet("color: red")
            reactor.callLater(5, self._reset_status)  # type: ignore
            error(self, "Error adding voucher", str(exc), self._traceback(exc))
            return
        payment_url = self.gateway.zkapauthorizer.zkap_payment_url(voucher)
        logging.debug("Opening payment URL %s ...", payment_url)
        self.status_label.setText("Launching browser...")
        if webbrowser.open(payment_url):
            logging.debug("Browser successfully launched")
            self.status_label.setText(
                "Browser window launched; please proceed to payment"
            )
        else:
            error(
                self,
                "Error launching browser",
                "Could not launch webbrower. To complete payment for "
                f"{self.gateway.name}, please visit the following URL:"
                f"<p><a href={payment_url}>{payment_url}</a><br>",
            )
            self.status_label.setText("Error launching browser")
            self.status_label.setStyleSheet("color: red")
        reactor.callLater(5, self._reset_status)  # type: ignore

    @Slot()
    def on_button_clicked(self) -> None:
        if self.is_commercial_grid:
            self._open_zkap_payment_url()
        else:
            self.on_voucher_link_clicked()

    def _update_info_label(self) -> None:
        zkapauthorizer = self.gateway.zkapauthorizer
        self.info_label.setText(
            f"Last purchase: {self._last_purchase_date} ("
            f"{self.chart_view.chart._convert(zkapauthorizer.zkap_batch_size)} "
            f"{zkapauthorizer.zkap_unit_name}s)     "
            f"Expected expiry: {self._expiry_date}"
        )

    @Slot(str)
    def on_zkaps_redeemed(self, timestamp: str) -> None:
        self._last_purchase_date = datetime.strftime(
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f"), "%d %b %Y"
        )
        self.zkaps_required_label.hide()
        self._reset_status()
        self.explainer_label.show()
        self.chart_view.show()
        self._update_info_label()

    def _update_chart(self) -> None:
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
        self.gui.main_window.toolbar.update_actions()  # XXX

    @Slot(int, int)
    def on_zkaps_updated(self, used: int, remaining: int) -> None:
        self._zkaps_used = used
        self._zkaps_remaining = remaining
        self._zkaps_total = used + remaining
        self._update_chart()

    @Slot(int, int)
    def on_zkaps_renewal_cost_updated(self, cost: int, period: int) -> None:
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
        action = "buy" if self.is_commercial_grid else "add"
        self.gui.show_message(
            "Low storage-time",
            f"Your storage-time is running low. Please {action} more "
            "storage-time to prevent data-loss.",
        )
        self.gui.main_window.show_usage_view()  # XXX
