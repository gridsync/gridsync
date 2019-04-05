# -*- coding: utf-8 -*-

import sys

from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QSystemTrayIcon

from gridsync import resource, settings
from gridsync.gui.menu import Menu


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, gui):
        super(SystemTrayIcon, self).__init__()
        self.gui = gui

        self.icon = QIcon(resource(settings['application']['tray_icon']))
        self.setIcon(self.icon)

        self.menu = Menu(self.gui)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_click)

        self.animation = QMovie()
        self.animation.setFileName(
            resource(settings['application']['tray_icon_sync']))
        self.animation.updated.connect(self.update)
        self.animation.setCacheMode(True)

    def update(self):
        if self.gui.core.operations:
            self.animation.setPaused(False)
            self.setIcon(QIcon(self.animation.currentPixmap()))
        else:
            self.animation.setPaused(True)
            self.setIcon(self.icon)

    def on_click(self, value):
        if value == QSystemTrayIcon.Trigger and sys.platform != 'darwin':
            self.gui.show_main_window()
