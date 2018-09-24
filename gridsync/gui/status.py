# -*- coding: utf-8 -*-

from humanize import naturalsize
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
        self.available_space = 0

        self.checkmark_icon = QLabel()
        self.checkmark_icon.setPixmap(
            QPixmap(resource('checkmark.png')).scaled(20, 20)
        )

        self.syncing_icon = QLabel()

        self.sync_movie = QMovie(resource('sync.gif'))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.updated.connect(
            lambda: self.syncing_icon.setPixmap(
                self.sync_movie.currentPixmap().scaled(20, 20)
            )
        )

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: dimgrey")

        self.on_sync_state_updated(0)

        self.tor_icon = QLabel()
        self.tor_icon.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(24, 24)
        )
        if not self.gateway.use_tor:
            self.tor_icon.hide()

        self.globe_icon = QLabel()
        self.globe_icon.setPixmap(
            QPixmap(resource('globe.png')).scaled(20, 20)
        )

        layout = QGridLayout(self)
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom - 2)
        layout.addWidget(self.checkmark_icon, 1, 1)
        layout.addWidget(self.syncing_icon, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addWidget(self.tor_icon, 1, 4)
        layout.addWidget(self.globe_icon, 1, 5)

        self.gateway.monitor.total_sync_state_updated.connect(
            self.on_sync_state_updated
        )
        self.gateway.monitor.space_updated.connect(self.on_space_updated)
        self.gateway.monitor.nodes_updated.connect(self.on_nodes_updated)

    def on_sync_state_updated(self, state):
        if state == 0:
            self.status_label.setText("Connecting...")
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.checkmark_icon.hide()
        elif state == 1:
            self.status_label.setText("Syncing")
            self.checkmark_icon.hide()
            self.syncing_icon.show()
            self.sync_movie.setPaused(False)
        elif state == 2:
            self.status_label.setText("Up to date")
            self.sync_movie.setPaused(True)
            self.syncing_icon.hide()
            self.checkmark_icon.show()

    def _update_grid_info_tooltip(self):
        if self.available_space:
            self.globe_icon.setToolTip(
                "Connected to {} of {} storage nodes\n{} available".format(
                    self.num_connected, self.num_known, self.available_space
                )
            )
        else:
            self.globe_icon.setToolTip(
                "Connected to {} of {} storage nodes".format(
                    self.num_connected, self.num_known
                )
            )

    def on_space_updated(self, space):
        self.available_space = naturalsize(space)
        self._update_grid_info_tooltip()

    def on_nodes_updated(self, connected, known):
        text = "Connected to {} of {} storage nodes".format(connected, known)
        self.status_label.setText(text)
        self.num_connected = connected
        self.num_known = known
        self._update_grid_info_tooltip()
