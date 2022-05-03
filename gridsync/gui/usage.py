# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import traceback
import webbrowser
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List

import attr
from humanize import naturalsize
from qtpy.QtCore import Qt, Slot
from qtpy.QtGui import QIcon, QPainter
from qtpy.QtWidgets import QGridLayout, QGroupBox, QLabel, QPushButton, QWidget
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync import APP_NAME, resource
from gridsync.desktop import get_browser_name
from gridsync.gui.charts import ZKAPBarChartView
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.voucher import VoucherCodeDialog
from gridsync.gui.widgets import VSpacer
from gridsync.msg import error
from gridsync.types import TwistedDeferred

if TYPE_CHECKING:
    from gridsync.gui import Gui  # pylint: disable=cyclic-import
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


def make_explainer_label() -> QLabel:
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


def make_redeeming_label() -> QLabel:
    redeeming_label = QLabel(
        "A voucher is being redeemed for storage-time. You may add folders "
        "during this time."
    )
    font = Font(10)
    font.setItalic(True)
    redeeming_label.setFont(font)
    redeeming_label.setAlignment(Qt.AlignCenter)
    redeeming_label.hide()
    return redeeming_label


def make_title() -> QLabel:
    title = QLabel("Storage-time")
    font = Font(11)
    font.setBold(True)
    title.setFont(font)
    title.setAlignment(Qt.AlignCenter)
    title.hide()
    return title


def make_info_label() -> QLabel:
    label = QLabel()
    label.setFont(Font(10))
    return label


def make_status_label() -> QLabel:
    status_label = QLabel(" ")
    status_label.setFont(Font(10))
    return status_label


def make_loading_storage_time() -> QLabel:
    label = QLabel("Loading storage-time information...")
    label.setAlignment(Qt.AlignCenter)
    label.setWordWrap(True)
    return label


@attr.s
class UsageView(QWidget):
    gateway: Tahoe = attr.ib()
    gui: Gui = attr.ib()

    _zkaps_used: int = attr.ib(default=0, init=False)
    _zkaps_cost: int = attr.ib(default=0, init=False)
    _zkaps_remaining: int = attr.ib(default=0, init=False)
    _zkaps_total: int = attr.ib(default=0, init=False)
    _zkaps_period: int = attr.ib(default=0, init=False)
    _redeeming_vouchers: List[str] = attr.ib(
        default=attr.Factory(list), init=False
    )
    _last_purchase_date: str = attr.ib(default="Not available", init=False)
    _expiry_date: str = attr.ib(default="Not available", init=False)
    _amount_stored: str = attr.ib(default="Not available", init=False)

    # Some of these widgets depend on the values of other attributes.  This is
    # okay as long as the dependency is of attributes defined lower on
    # attributes defined higher.  attrs will initialize the attributes in the
    # order they are defined on the class.
    title = attr.ib(default=attr.Factory(make_title), init=False)
    explainer_label = attr.ib(
        default=attr.Factory(make_explainer_label), init=False
    )
    redeeming_label = attr.ib(
        default=attr.Factory(make_redeeming_label), init=False
    )
    # The rest of these don't use attr.Factory because they depend on
    # something from self or they're so trivial there didn't seem to be a
    # point exposing the logic to outsiders.
    loading_storage_time = attr.ib(
        default=attr.Factory(make_loading_storage_time), init=False
    )
    zkaps_required_label = attr.ib(init=False)
    chart_view = attr.ib(init=False)
    info_label = attr.ib(default=attr.Factory(make_info_label), init=False)
    button = attr.ib(init=False)
    voucher_link = attr.ib(init=False)
    status_label = attr.ib(default=attr.Factory(make_status_label), init=False)
    groupbox = attr.ib(init=False)

    @zkaps_required_label.default
    def _zkaps_required_label_default(self) -> QLabel:
        if self.is_commercial_grid:
            action = "buy storage-time"
        else:
            action = "add storage-time using a voucher code"
        zkaps_required_label = QLabel(
            "You currently have 0 GB-months available.\n\nIn order to store "
            f"data with {self.gateway.name}, you will need to {action}."
        )
        zkaps_required_label.setAlignment(Qt.AlignCenter)
        zkaps_required_label.setWordWrap(True)
        zkaps_required_label.hide()
        return zkaps_required_label

    @chart_view.default
    def _chart_view_default(self) -> ZKAPBarChartView:
        chart_view = ZKAPBarChartView(self.gateway)
        chart_view.setFixedHeight(128)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.hide()
        return chart_view

    @button.default
    def _button_default(self) -> QPushButton:
        if self.is_commercial_grid:
            browser = get_browser_name()
            button = QPushButton(f"Buy storage-time in {browser} ")
            button.setIcon(QIcon(resource("globe-white.png")))
            button.setLayoutDirection(Qt.RightToLeft)
        else:
            button = QPushButton("Use voucher code")
        button.setStyleSheet("background: green; color: white")
        button.setFixedSize(240, 32)
        button.clicked.connect(self.on_button_clicked)
        return button

    @voucher_link.default
    def _voucher_link_default(self) -> QLabel:
        voucher_link = QLabel("<a href>I have a voucher code</a>")
        voucher_link.linkActivated.connect(self.on_voucher_link_clicked)
        if not self.is_commercial_grid:
            voucher_link.hide()
        return voucher_link

    @groupbox.default
    def _groupbox_default(self) -> QGroupBox:
        layout = QGridLayout()
        layout.addItem(VSpacer(), 10, 0)
        layout.addWidget(self.title, 20, 0)
        layout.addWidget(self.explainer_label, 30, 0)
        layout.addWidget(self.redeeming_label, 30, 0)
        layout.addWidget(self.zkaps_required_label, 40, 0)
        layout.addWidget(self.loading_storage_time, 50, 0)
        layout.addItem(VSpacer(), 50, 0)
        layout.addWidget(self.chart_view, 60, 0)
        layout.addWidget(self.info_label, 70, 0, Qt.AlignCenter)
        layout.addItem(VSpacer(), 80, 0)
        layout.addWidget(self.button, 90, 0, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.voucher_link, 100, 0, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.status_label, 110, 0, 1, 1, Qt.AlignCenter)
        layout.addItem(VSpacer(), 110, 0)

        groupbox = QGroupBox()
        groupbox.setLayout(layout)

        main_layout = QGridLayout(self)
        main_layout.addWidget(groupbox)

        return groupbox

    @property
    def is_commercial_grid(self) -> bool:
        return "zkap_payment_url_root" in self.gateway.settings

    def __attrs_pre_init__(self) -> None:
        # Accessing Slot() attributes is broken until QWidget is initialized.
        # If we don't force that to happen here then any attr.ib defaults that
        # depend on `self` have trouble.
        super().__init__()

    def __attrs_post_init__(self) -> None:
        # Do a bunch of other initialization that doesn't obviously belong to
        # one of the attributes on self that we had to initialize.
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
        self.gateway.monitor.redeeming_vouchers_updated.connect(
            self.on_redeeming_vouchers_updated
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
        bs = self.chart_view.chart()._convert(zkapauthorizer.zkap_batch_size)
        self.info_label.setText(
            f"Last purchase: {self._last_purchase_date} "
            f"({bs} {zkapauthorizer.zkap_unit_name}s)     "
            f"Expected expiry: {self._expiry_date}"
        )

    @Slot(str)
    def on_zkaps_redeemed(self, timestamp: str) -> None:
        self._last_purchase_date = datetime.strftime(
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f"), "%d %b %Y"
        )
        self._reset_status()
        self._update_chart()
        self._update_info_label()

    def _update_chart(self) -> None:
        self.loading_storage_time.hide()
        if self._redeeming_vouchers:
            self.zkaps_required_label.hide()
            self.explainer_label.hide()
            self.title.show()
            self.redeeming_label.show()
            self.chart_view.show()
        elif self._zkaps_remaining:
            self.zkaps_required_label.hide()
            self.redeeming_label.hide()
            self.title.show()
            self.explainer_label.show()
            self.chart_view.show()
        else:
            self.title.hide()
            self.explainer_label.hide()
            self.redeeming_label.hide()
            self.chart_view.hide()
            self.zkaps_required_label.show()
        self.chart_view.chart().update_chart(
            self._zkaps_used,
            self._zkaps_cost,
            self._zkaps_remaining,
            self._zkaps_period,
        )
        self.gui.main_window.toolbar.update_actions()  # XXX

    @Slot(list)
    def on_redeeming_vouchers_updated(self, vouchers: List) -> None:
        self._redeeming_vouchers = vouchers
        self._update_chart()

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
