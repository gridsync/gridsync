# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from qtpy.QtGui import QIcon, QMovie, QPixmap
from qtpy.QtWidgets import QSystemTrayIcon

if TYPE_CHECKING:
    from gridsync.gui import Gui

from gridsync import resource, settings
from gridsync.gui.menu import Menu
from gridsync.gui.pixmap import BadgedPixmap


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, gui: Gui) -> None:
        super().__init__()
        self.gui = gui
        self._operations: set = set()

        tray_icon_path = resource(settings["application"]["tray_icon"])
        self.app_pixmap = QPixmap(tray_icon_path)
        self.app_icon = QIcon(tray_icon_path)
        self.setIcon(self.app_icon)

        self.menu = Menu(self.gui)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_click)

        self.messageClicked.connect(self.gui.show_main_window)

        self.animation = QMovie()
        self.animation.setFileName(
            resource(settings["application"]["tray_icon_sync"])
        )
        self.animation.updated.connect(self.update)
        self.animation.setCacheMode(QMovie.CacheAll)

    def add_operation(self, operation: tuple) -> None:
        self._operations.add(operation)

    def remove_operation(self, operation: tuple) -> None:
        try:
            self._operations.remove(operation)
        except KeyError:
            pass

    def update(self) -> None:
        if self._operations:
            self.animation.setPaused(False)
            pixmap = self.animation.currentPixmap()
            if self.gui.unread_messages:
                pixmap = BadgedPixmap(
                    pixmap, len(self.gui.unread_messages), 0.6
                )
            self.setIcon(QIcon(pixmap))
        else:
            self.animation.setPaused(True)
            if self.gui.unread_messages:
                self.setIcon(
                    QIcon(
                        BadgedPixmap(
                            self.app_pixmap, len(self.gui.unread_messages), 0.6
                        )
                    )
                )
            else:
                self.setIcon(self.app_icon)

    def on_click(self, value: int) -> None:
        if value == QSystemTrayIcon.Trigger and sys.platform != "darwin":
            self.gui.show_main_window()
