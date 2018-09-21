# -*- coding: utf-8 -*-

from PyQt5.QtGui import QMovie, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout, QLabel, QSizePolicy, QSpacerItem, QWidget)

from gridsync import resource


class StatusPanel(QWidget):
    def __init__(self, gateway):
        super(StatusPanel, self).__init__()
        self.gateway = gateway
        self.icon_checkmark = QLabel()
        self.icon_checkmark.setPixmap(
            QPixmap(resource('checkmark.png')).scaled(20, 20)
        )
        self.icon_checkmark.hide()

        self.icon_syncing = QLabel()
        self.icon_syncing.hide()

        self.sync_movie = QMovie(resource('sync.gif'))
        self.sync_movie.setCacheMode(True)
        self.sync_movie.updated.connect(
            lambda: self.icon_syncing.setPixmap(
                self.sync_movie.currentPixmap().scaled(20, 20)
            )
        )

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: dimgrey")

        self.icon_onion = QLabel()
        self.icon_onion.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(24, 24)
        )

        layout = QGridLayout(self)
        left, _, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(left, 0, right, bottom - 2)
        layout.addWidget(self.icon_checkmark, 1, 1)
        layout.addWidget(self.icon_syncing, 1, 1)
        layout.addWidget(self.status_label, 1, 2)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 3)
        layout.addWidget(self.icon_onion, 1, 4)

        self.gateway.monitor.total_sync_state_updated.connect(
            self.on_sync_state_updated
        )

    def on_sync_state_updated(self, state):
        if state == 1:
            self.status_label.setText("Syncing")
            self.icon_checkmark.hide()
            self.icon_syncing.show()
            self.sync_movie.setPaused(False)
        elif state == 2:
            self.status_label.setText("Up to date")
            self.sync_movie.setPaused(True)
            self.icon_syncing.hide()
            self.icon_checkmark.show()
