# -*- coding: utf-8 -*-

import sys

from PyQt5.QtGui import QIcon, QMovie, QPixmap
from PyQt5.QtWidgets import QSystemTrayIcon

from gridsync import resource, settings
from gridsync.gui.menu import Menu
from gridsync.gui.pixmap import BadgedPixmap


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, gui):
        super(SystemTrayIcon, self).__init__()
        self.gui = gui

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
        self.animation.setCacheMode(True)

    def update(self):
        if self.gui.core.operations:
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

    def on_click(self, value):
        if value == QSystemTrayIcon.Trigger and sys.platform != "darwin":
            self.gui.show_main_window()
