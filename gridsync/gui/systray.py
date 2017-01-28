# -*- coding: utf-8 -*-

import logging
import webbrowser

from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon
from twisted.internet import reactor

from gridsync import resource, settings


def open_documentation():
    webbrowser.open(settings['help']['docs_url'])


def open_issue():
    webbrowser.open(settings['help']['issues_url'])


class Menu(QMenu):
    def __init__(self, parent):
        super(self.__class__, self).__init__()
        self.parent = parent
        self.populate()

    def populate(self):
        self.clear()
        logging.debug("(Re-)populating systray menu...")
        name = settings['application']['name']

        open_action = QAction(QIcon(''), "Open {}".format(name), self)
        open_action.triggered.connect(self.parent.parent.show_main_window)

        documentation_action = QAction(
            QIcon(''), "Browse Documentation...", self)
        documentation_action.triggered.connect(open_documentation)

        issue_action = QAction(QIcon(''), "Report Issue...", self)
        issue_action.triggered.connect(open_issue)

        about_action = QAction(QIcon(''), "About {}...".format(name), self)
        about_action.setEnabled(False)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")
        help_menu.addAction(documentation_action)
        help_menu.addAction(issue_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

        quit_action = QAction(
            QIcon(''), "&Quit {}".format(name), self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(reactor.stop)

        self.addAction(open_action)
        self.addMenu(help_menu)
        self.addSeparator()
        self.addAction(quit_action)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(self.__class__, self).__init__()
        self.parent = parent

        self.setIcon(QIcon(resource(settings['application']['tray_icon'])))

        self.menu = Menu(self)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_click)

        self.animation = QMovie()
        self.animation.setFileName(
            resource(settings['application']['tray_icon_sync']))
        self.animation.updated.connect(self.update_animation_frame)
        self.animation.setCacheMode(True)

    def update_animation_frame(self):
        self.setIcon(QIcon(self.animation.currentPixmap()))

    def set_icon(self, resource_file):
        self.setIcon(QIcon(resource(resource_file)))

    def on_click(self, value):  # pylint: disable=no-self-use
        if value == QSystemTrayIcon.Trigger:
            self.parent.main_window.show()
