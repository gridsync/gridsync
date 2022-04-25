# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from humanize import naturalsize
from qtpy.QtCore import QSize, Qt, Slot
from qtpy.QtGui import QIcon, QMovie
from qtpy.QtWidgets import QAction, QGridLayout, QLabel, QToolButton, QWidget

from gridsync import resource

if TYPE_CHECKING:
    from gridsync.gui import Gui
    from gridsync.tahoe import Tahoe

# from gridsync.gui.charts import ZKAPCompactPieChartView
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.menu import Menu
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.widgets import HSpacer
from gridsync.magic_folder import MagicFolderStatus


class StatusPanel(QWidget):
    def __init__(self, gateway: Tahoe, gui: Gui) -> None:
        super().__init__()
        self.gateway = gateway
        self.gui = gui

        self.status = MagicFolderStatus.LOADING
        self.num_connected = 0
        self.num_known = 0
        self.available_space = 0

        self.checkmark_icon = QLabel()
        self.checkmark_icon.setPixmap(Pixmap("checkmark.png", 20))

        self.error_icon = QLabel()
        self.error_icon.setPixmap(Pixmap("alert-circle-red.png", 20))

        self.syncing_icon = QLabel()

        self.sync_movie = QMovie(resource("sync.gif"))
        self.sync_movie.setCacheMode(QMovie.CacheAll)
        self.sync_movie.updated.connect(
            lambda: self.syncing_icon.setPixmap(
                self.sync_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        )

        self.status_label = QLabel()
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color(), 0.6
        ).name()
        self.status_label.setStyleSheet(f"QLabel {{ color: {dimmer_grey} }}")
        self.status_label.setFont(Font(10))

        self.setMaximumHeight(32)

        self.setStyleSheet("QToolButton { border: none }")
        # self.setStyleSheet("""
        #    QToolButton { color: dimgrey; border: none; }
        #    QToolButton:hover {
        #        background-color: #FAFAFA;
        #        border: 1px solid grey;
        #        border-radius: 2px;
        #    }
        # """)

        self.tor_button = QToolButton()
        self.tor_button.setIconSize(QSize(20, 20))
        self.tor_action = QAction(
            QIcon(resource("tor-onion.png")),
            "This connection is being routed through the Tor network",
        )
        self.tor_button.setDefaultAction(self.tor_action)
        self.tor_button.setStyleSheet("QToolButton { border: none }")
        if self.gateway.use_tor:
            self.connection_mode = " via Tor"
        else:
            self.connection_mode = ""
            self.tor_button.hide()

        preferences_button = QToolButton(self)
        preferences_button.setIcon(QIcon(resource("preferences.png")))
        preferences_button.setIconSize(QSize(20, 20))
        preferences_button.setMenu(Menu(self.gui, show_open_action=False))
        preferences_button.setPopupMode(QToolButton.InstantPopup)
        preferences_button.setStyleSheet(
            "QToolButton { border: none }"
            "QToolButton::menu-indicator { image: none }"
        )

        # zkap_chart_view = ZKAPCompactPieChartView()

        # self.zkap_label = QLabel()
        # self.zkap_label.setStyleSheet(f"color: {dimmer_grey}")
        # self.zkap_label.hide()

        self.stored_label = QLabel()
        self.stored_label.setStyleSheet(f"color: {dimmer_grey}")
        self.stored_label.hide()

        self.expires_label = QLabel()
        self.expires_label.setStyleSheet(f"color: {dimmer_grey}")
        self.expires_label.hide()

        layout = QGridLayout(self)
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom - 2)
        layout.addWidget(self.checkmark_icon, 1, 1)
        layout.addWidget(self.error_icon, 1, 1)
        layout.addWidget(self.syncing_icon, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        # layout.addWidget(zkap_chart_view, 1, 5)
        # layout.addWidget(self.zkap_label, 1, 5)
        layout.addWidget(self.stored_label, 1, 6)
        layout.addWidget(self.expires_label, 1, 7)
        layout.addWidget(self.tor_button, 1, 8)
        layout.addWidget(preferences_button, 1, 9)

        self.gateway.monitor.space_updated.connect(self.on_space_updated)
        self.gateway.monitor.nodes_updated.connect(self.on_nodes_updated)
        # self.gateway.monitor.zkaps_updated.connect(self.on_zkaps_updated)
        self.gateway.magic_folder.monitor.total_folders_size_updated.connect(
            self.on_total_folders_size_updated
        )
        self.gateway.monitor.days_remaining_updated.connect(
            self.on_days_remaining_updated
        )
        self.gateway.magic_folder.monitor.overall_status_changed.connect(
            self.on_sync_status_updated
        )

        self.on_sync_status_updated(self.status)

    def _update_status_label(self) -> None:
        if self.status in (
            MagicFolderStatus.LOADING,
            MagicFolderStatus.WAITING,
        ):
            if self.gateway.shares_happy:
                if self.num_connected < self.gateway.shares_happy:
                    self.status_label.setText(
                        f"Connecting to {self.gateway.name} "
                        f"({self.num_connected}/{self.gateway.shares_happy})"
                        f"{self.connection_mode}..."
                    )
                else:
                    self.status_label.setText(
                        f"Connected to {self.gateway.name}"
                        f"{self.connection_mode}"
                    )
            else:
                self.status_label.setText(
                    f"Connecting to {self.gateway.name}"
                    f"{self.connection_mode}..."
                )
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.checkmark_icon.hide()
            self.error_icon.hide()
        elif self.status == MagicFolderStatus.SYNCING:
            self.status_label.setText("Syncing")
            self.checkmark_icon.hide()
            self.error_icon.hide()
            self.syncing_icon.show()
            self.sync_movie.setPaused(False)
        elif self.status == MagicFolderStatus.UP_TO_DATE:
            self.status_label.setText("Up to date")
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.error_icon.hide()
            self.checkmark_icon.show()
        elif self.status == MagicFolderStatus.ERROR:
            self.status_label.setText("Error syncing folder")
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.checkmark_icon.hide()
            self.error_icon.show()
        if self.available_space:
            self.status_label.setToolTip(
                "Connected to {} of {} storage nodes\n{} available".format(
                    self.num_connected, self.num_known, self.available_space
                )
            )
        else:
            self.status_label.setToolTip(
                "Connected to {} of {} storage nodes".format(
                    self.num_connected, self.num_known
                )
            )

    def on_sync_status_updated(self, status: MagicFolderStatus) -> None:
        self.status = status
        self._update_status_label()

    def on_space_updated(self, bytes_available: int) -> None:
        self.available_space = naturalsize(bytes_available)
        self._update_status_label()

    def on_nodes_updated(self, connected: int, known: int) -> None:
        self.num_connected = connected
        self.num_known = known
        self._update_status_label()

    # @Slot(int, int)
    # def on_zkaps_updated(self, used: int, remaining: int) -> None:
    #    total = used + remaining
    #    self.zkap_label.setToolTip(
    #        f"{self.gateway.zkapauthorizer.zkap_name}s:\n\nUsed: {used}\n"
    #        f"Total: {total}\nAvailable: {remaining}"
    #    )
    #    if remaining and remaining >= 1000:
    #        remaining = str(round(remaining / 1000, 1)) + "k"  # type: ignore
    #    self.zkap_label.setText(
    #        f"{self.gateway.zkapauthorizer.zkap_name_abbrev}s "
    #        f"available: {remaining} "
    #    )
    #    self.zkap_label.show()

    @Slot(object)
    def on_total_folders_size_updated(self, size: int) -> None:
        if self.expires_label.text():
            self.stored_label.setText(f"Stored: {naturalsize(size)},")
        else:
            self.stored_label.setText(f"Stored: {naturalsize(size)}")
        self.stored_label.show()

    @Slot(int)
    def on_days_remaining_updated(self, days: int) -> None:
        expiry_date = datetime.strftime(
            datetime.strptime(
                datetime.isoformat(datetime.now() + timedelta(days=days)),
                "%Y-%m-%dT%H:%M:%S.%f",
            ),
            "%d %b %Y",
        )
        self.expires_label.setText(f"Expected expiry: {expiry_date}")
        self.expires_label.show()
