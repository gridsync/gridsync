# -*- coding: utf-8 -*-

from humanize import naturalsize
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import (
    QAction,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QWidget,
)

from gridsync import resource
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.menu import Menu
from gridsync.gui.pixmap import Pixmap


class StatusPanel(QWidget):
    def __init__(self, gateway, gui):
        super(StatusPanel, self).__init__()
        self.gateway = gateway
        self.gui = gui

        self.state = 0
        self.num_connected = 0
        self.num_known = 0
        self.available_space = 0

        self.globe_icon = QLabel(self)
        self.globe_icon.setPixmap(Pixmap("globe.png", 20))

        self.checkmark_icon = QLabel()
        self.checkmark_icon.setPixmap(Pixmap("checkmark.png", 20))

        self.loading_icon = QLabel(self)
        self.loading_movie = QMovie(resource("waiting.gif"))
        self.loading_movie.setCacheMode(True)
        self.loading_movie.updated.connect(
            lambda: self.loading_icon.setPixmap(
                self.loading_movie.currentPixmap().scaled(
                    20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            )
        )

        self.syncing_icon = QLabel()

        self.sync_movie = QMovie(resource("sync.gif"))
        self.sync_movie.setCacheMode(True)
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
        self.status_label.setStyleSheet("color: {}".format(dimmer_grey))
        self.status_label.setFont(Font(10))

        self.on_sync_state_updated(0)

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
        if not self.gateway.use_tor:
            self.tor_button.hide()

        self.globe_button = QToolButton()
        self.globe_button.setIconSize(QSize(20, 20))
        self.globe_action = QAction(QIcon(resource("globe.png")), "")
        self.globe_button.setDefaultAction(self.globe_action)

        preferences_button = QToolButton(self)
        preferences_button.setIcon(QIcon(resource("preferences.png")))
        preferences_button.setIconSize(QSize(20, 20))
        preferences_button.setMenu(Menu(self.gui, show_open_action=False))
        preferences_button.setPopupMode(2)
        preferences_button.setStyleSheet(
            "QToolButton::menu-indicator { image: none }"
        )

        layout = QGridLayout(self)
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom - 2)
        layout.addWidget(self.globe_icon, 1, 1)
        layout.addWidget(self.checkmark_icon, 1, 1)
        layout.addWidget(self.loading_icon, 1, 1)
        layout.addWidget(self.syncing_icon, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addWidget(self.tor_button, 1, 4)
        layout.addWidget(self.globe_button, 1, 5)
        layout.addWidget(preferences_button, 1, 6)

        self.gateway.monitor.total_sync_state_updated.connect(
            self.on_sync_state_updated
        )
        self.gateway.monitor.space_updated.connect(self.on_space_updated)
        self.gateway.monitor.nodes_updated.connect(self.on_nodes_updated)

    def _update_status_label(self):
        text = ""
        if self.state == 0:
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.checkmark_icon.hide()
            if self.gateway.shares_happy:
                if self.num_connected < self.gateway.shares_happy:
                    text = (
                        f"Connecting to {self.gateway.name} ("
                        f"{self.num_connected}/{self.gateway.shares_happy})..."
                    )
                    self.globe_icon.hide()
                    self.loading_icon.show()
                    self.loading_movie.setPaused(False)
                else:
                    text = f"Connected to {self.gateway.name}"
                    self.globe_icon.show()
                    self.loading_icon.hide()
                    self.loading_movie.setPaused(True)

            else:
                text = f"Connecting to {self.gateway.name}..."
                self.globe_icon.hide()
                self.loading_icon.show()
                self.loading_movie.setPaused(False)
        elif self.state == 1:
            text = "Syncing"
            self.loading_movie.setPaused(True)
            self.loading_icon.hide()
            self.globe_icon.hide()
            self.checkmark_icon.hide()
            self.syncing_icon.show()
            self.sync_movie.setPaused(False)
        elif self.state == 2:
            text = "Up to date"
            self.loading_movie.setPaused(True)
            self.sync_movie.setPaused(True)
            self.loading_icon.hide()
            self.syncing_icon.hide()
            self.globe_icon.hide()
            self.checkmark_icon.show()
        self.status_label.setText(text)
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

    def on_sync_state_updated(self, state):
        self.state = state
        self._update_status_label()

    def on_space_updated(self, space):
        self.available_space = naturalsize(space)
        self._update_status_label()

    def on_nodes_updated(self, connected, known):
        self.num_connected = connected
        self.num_known = known
        self._update_status_label()
