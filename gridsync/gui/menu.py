# -*- coding: utf-8 -*-

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QAction, QMenu, QMessageBox

from gridsync import (
    APP_NAME,
    DOCS_HELP_URL,
    ISSUES_HELP_URL,
    __version__,
    resource,
    settings,
)

if TYPE_CHECKING:
    from gridsync.gui import AbstractGui


class Menu(QMenu):
    def __init__(self, gui: AbstractGui, show_open_action: bool = True):
        super().__init__()
        self.gui = gui

        self.about_msg = QMessageBox()
        self.about_msg.setWindowTitle("{} - About".format(APP_NAME))
        app_icon = QIcon(resource(settings["application"]["tray_icon"]))
        self.about_msg.setIconPixmap(app_icon.pixmap(64, 64))
        self.about_msg.setText("{} {}".format(APP_NAME, __version__))
        self.about_msg.setWindowModality(Qt.WindowModal)

        if show_open_action:
            open_action = QAction(QIcon(""), "Open {}".format(APP_NAME), self)
            open_action.triggered.connect(self.gui.show)
            self.addAction(open_action)
            self.addSeparator()

        preferences_action = QAction(QIcon(""), "Preferences...", self)
        preferences_action.triggered.connect(self.gui.show_preferences_window)
        self.addAction(preferences_action)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")
        if DOCS_HELP_URL:
            docs_action = QAction(QIcon(""), "Browse Documentation...", self)
            docs_action.triggered.connect(
                lambda: webbrowser.open(DOCS_HELP_URL)
            )
            help_menu.addAction(docs_action)
        if ISSUES_HELP_URL:
            issue_action = QAction(QIcon(""), "Report Issue...", self)
            issue_action.triggered.connect(
                lambda: webbrowser.open(ISSUES_HELP_URL)
            )
            help_menu.addAction(issue_action)
        export_action = QAction(QIcon(""), "View Debug Information...", self)
        export_action.triggered.connect(self.gui.show_debug_exporter)
        help_menu.addAction(export_action)
        help_menu.addSeparator()
        about_action = QAction(QIcon(""), "About {}...".format(APP_NAME), self)
        about_action.triggered.connect(self.about_msg.open)
        help_menu.addAction(about_action)
        self.about_action = about_action  # Make accessible to tests
        self.addMenu(help_menu)

        self.addSeparator()

        quit_action = QAction(QIcon(""), "&Quit {}".format(APP_NAME), self)
        quit_action.triggered.connect(self.gui.main_window.confirm_quit)
        self.addAction(quit_action)
