# -*- coding: utf-8 -*-

import logging
import sys
import webbrowser

from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox, QSystemTrayIcon
from twisted.internet import reactor

from gridsync import resource, settings, APP_NAME


def open_documentation():
    webbrowser.open(settings['help']['docs_url'])


def open_issue():
    webbrowser.open(settings['help']['issues_url'])


class Menu(QMenu):
    def __init__(self, parent):
        super(Menu, self).__init__()
        self.parent = parent
        self.populate()

    def populate(self):
        self.clear()
        logging.debug("(Re-)populating systray menu...")

        open_action = QAction(QIcon(''), "Open {}".format(APP_NAME), self)
        open_action.triggered.connect(self.parent.parent.show_main_window)

        documentation_action = QAction(
            QIcon(''), "Browse Documentation...", self)
        documentation_action.triggered.connect(open_documentation)

        issue_action = QAction(QIcon(''), "Report Issue...", self)
        issue_action.triggered.connect(open_issue)

        about_action = QAction(QIcon(''), "About {}...".format(APP_NAME), self)
        about_action.setEnabled(False)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")
        help_menu.addAction(documentation_action)
        help_menu.addAction(issue_action)
        help_menu.addSeparator()
        help_menu.addAction(about_action)

        quit_action = QAction(
            QIcon(''), "&Quit {}".format(APP_NAME), self)
        quit_action.triggered.connect(self.confirm_quit)

        self.addAction(open_action)
        self.addMenu(help_menu)
        self.addSeparator()
        self.addAction(quit_action)

    def confirm_quit(self):
        reply = QMessageBox.question(
            self, "Exit {}?".format(APP_NAME),
            "Are you sure you wish to quit? If you quit, {} will stop "
            "synchronizing your folders until you run it again.".format(
                APP_NAME),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            reactor.stop()


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(SystemTrayIcon, self).__init__()
        self.parent = parent

        self.icon = QIcon(resource(settings['application']['tray_icon']))
        self.setIcon(self.icon)

        self.menu = Menu(self)
        self.setContextMenu(self.menu)
        self.activated.connect(self.on_click)

        self.animation = QMovie()
        self.animation.setFileName(
            resource(settings['application']['tray_icon_sync']))
        self.animation.updated.connect(self.update)
        self.animation.setCacheMode(True)

    def update(self):
        if self.parent.core.operations:
            self.animation.setPaused(False)
            self.setIcon(QIcon(self.animation.currentPixmap()))
        else:
            self.animation.setPaused(True)
            self.setIcon(self.icon)

    def on_click(self, value):
        if value == QSystemTrayIcon.Trigger and sys.platform != 'darwin':
            self.parent.show_main_window()
