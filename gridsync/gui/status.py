# -*- coding: utf-8 -*-

from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout, QLabel, QSizePolicy, QSpacerItem, QWidget)

from gridsync import resource


class StatusPanel(QWidget):
    def __init__(self, gateway):
        super(StatusPanel, self).__init__()
        self.gateway = gateway

        self.num_connected = 0
        self.num_known = 0

        self.icon_checkmark = QLabel()
        self.icon_checkmark.setPixmap(
            QPixmap(resource('checkmark.png')).scaled(20, 20)
        )

        self.icon_syncing = QLabel()

        self.sync_movie = QMovie(resource('sync.gif'))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.updated.connect(
            lambda: self.icon_syncing.setPixmap(
                self.sync_movie.currentPixmap().scaled(20, 20)
            )
        )

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: dimgrey")

        self.on_sync_state_updated(0)

        self.icon_onion = QLabel()
        self.icon_onion.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(24, 24)
        )
        if not self.gateway.use_tor:
            self.icon_onion.hide()

        self.globe_icon = QLabel()
        self.globe_icon.setPixmap(
            QPixmap(resource('globe.png')).scaled(20, 20)
        )

        layout = QGridLayout(self)
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom - 2)
        layout.addWidget(self.icon_checkmark, 1, 1)
        layout.addWidget(self.icon_syncing, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addWidget(self.icon_onion, 1, 4)
        layout.addWidget(self.globe_icon, 1, 5)

        self.gateway.monitor.total_sync_state_updated.connect(
            self.on_sync_state_updated
        )
        self.gateway.monitor.nodes_updated.connect(self.on_nodes_updated)

    def on_sync_state_updated(self, state):
        if state == 0:
            self.status_label.setText("Connecting...")
            self.sync_movie.setPaused(True)
            self.icon_syncing.hide()
            self.icon_checkmark.hide()
        elif state == 1:
            self.status_label.setText("Syncing")
            self.icon_checkmark.hide()
            self.icon_syncing.show()
            self.sync_movie.setPaused(False)
        elif state == 2:
            self.status_label.setText("Up to date")
            self.sync_movie.setPaused(True)
            self.icon_syncing.hide()
            self.icon_checkmark.show()

    def on_nodes_updated(self, connected, known):
        text = "Connected to {} of {} storage nodes".format(connected, known)
        self.status_label.setText(text)
        self.globe_icon.setToolTip(text)
        self.num_connected = connected
        self.num_known = known
