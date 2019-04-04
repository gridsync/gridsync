# -*- coding: utf-8 -*-

import logging
import webbrowser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox

from gridsync import resource, settings, APP_NAME
from gridsync._version import __version__


def open_documentation():
    webbrowser.open(settings['help']['docs_url'])


def open_issue():
    webbrowser.open(settings['help']['issues_url'])


class Menu(QMenu):
    def __init__(self, parent):
        super(Menu, self).__init__()
        self.parent = parent
        self.gui = self.parent.parent

        self.about_msg = QMessageBox()
        self.about_msg.setWindowTitle("{} - About".format(APP_NAME))
        app_icon = QIcon(resource(settings['application']['tray_icon']))
        self.about_msg.setIconPixmap(app_icon.pixmap(64, 64))
        self.about_msg.setText("{} {}".format(APP_NAME, __version__))
        self.about_msg.setWindowModality(Qt.WindowModal)

        self.populate()

    def populate(self):
        self.clear()
        logging.debug("(Re-)populating systray menu...")

        open_action = QAction(QIcon(''), "Open {}".format(APP_NAME), self)
        open_action.triggered.connect(self.gui.show)
        self.addAction(open_action)

        self.addSeparator()

        preferences_action = QAction(QIcon(''), "Preferences...", self)
        preferences_action.triggered.connect(self.gui.show_preferences_window)
        self.addAction(preferences_action)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")
        help_settings = settings.get('help')
        if help_settings:
            if help_settings.get('docs_url'):
                docs_action = QAction(
                    QIcon(''), "Browse Documentation...", self)
                docs_action.triggered.connect(open_documentation)
                help_menu.addAction(docs_action)
            if help_settings.get('issues_url'):
                issue_action = QAction(QIcon(''), "Report Issue...", self)
                issue_action.triggered.connect(open_issue)
                help_menu.addAction(issue_action)
        export_action = QAction(QIcon(''), "Export Debug Information...", self)
        export_action.triggered.connect(self.gui.show_debug_exporter)
        help_menu.addAction(export_action)
        help_menu.addSeparator()
        about_action = QAction(QIcon(''), "About {}...".format(APP_NAME), self)
        about_action.triggered.connect(self.about_msg.exec_)
        help_menu.addAction(about_action)
        self.addMenu(help_menu)

        self.addSeparator()

        quit_action = QAction(
            QIcon(''), "&Quit {}".format(APP_NAME), self)
        quit_action.triggered.connect(self.gui.main_window.confirm_quit)
        self.addAction(quit_action)
