# -*- coding: utf-8 -*-

import logging
import os
import shutil
import subprocess
import sys
import webbrowser

from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import (
    QAction, QMainWindow, QMenu, QMessageBox, QSystemTrayIcon)
from twisted.internet import reactor

from gridsync import config_dir, settings
from gridsync.forms.preferences import Ui_MainWindow as Preferences
from gridsync.invite import InviteForm
from gridsync.newfolder import NewFolderWindow
from gridsync.resource import resource


class PreferencesWindow(QMainWindow):
    def __init__(self):
        super(PreferencesWindow, self).__init__()
        self.ui = Preferences()
        self.ui.setupUi(self)


class RightClickMenu(QMenu):
    def __init__(self, parent):
        super(RightClickMenu, self).__init__()
        self.parent = parent
        self.invite_form = None
        self.populate()

    def populate(self):
        self.clear()
        logging.debug("(Re-)populating systray menu...")

        invite_action = QAction(QIcon(""), "Enter Invite Code...", self)
        invite_action.triggered.connect(self.show_invite_form)
        self.addAction(invite_action)

        new_folder_action = QAction(QIcon(""), "Add New Sync Folder...", self)
        #new_folder_action.triggered.connect(
        #    self.parent.new_folder_window.populate_combo_box)
        new_folder_action.triggered.connect(self.parent.new_folder_window.show)
        if sys.platform == 'darwin':
            new_folder_action.triggered.connect(
                self.parent.new_folder_window.raise_)
        self.addAction(new_folder_action)

        #open_action = QAction(QIcon(""), "Open Gridsync Folder", self)
        #open_action.triggered.connect(open_gridsync_folder)
        #self.addAction(open_action)

        snapshots_action = QAction(QIcon(""), "Browse Snapshots...", self)
        #snapshots_action.setEnabled(False)
        self.addAction(snapshots_action)

        self.addSeparator()

        status_action = QAction(
            QIcon(""), self.parent.parent.status_text, self)
        status_action.setEnabled(False)
        self.addAction(status_action)

        pause_action = QAction(QIcon(""), "Pause Syncing", self)
        self.addAction(pause_action)

        self.addSeparator()

        preferences_action = QAction(QIcon(""), "Preferences...", self)
        preferences_action.triggered.connect(
            self.parent.preferences_window.show)
        if sys.platform == 'darwin':
            preferences_action.triggered.connect(
                self.parent.preferences_window.raise_)
        self.addAction(preferences_action)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")

        documentation_action = QAction(
            QIcon(""), "Online Documentation...", self)
        documentation_action.triggered.connect(open_online_documentation)
        help_menu.addAction(documentation_action)

        issues_action = QAction(QIcon(""), "GitHub Issues...", self)
        issues_action.triggered.connect(open_github_issues)
        help_menu.addAction(issues_action)

        help_menu.addSeparator()

        about_action = QAction(QIcon(""), "About Gridsync", self)
        help_menu.addAction(about_action)

        self.addMenu(help_menu)

        self.addSeparator()

        quit_action = QAction(QIcon(""), '&Quit Gridsync', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(reactor.stop)
        self.addAction(quit_action)

    def show_invite_form(self):
        nodedir = os.path.join(config_dir, 'default')
        if os.path.isdir(nodedir):
            reply = QMessageBox.question(
                self, "Tahoe-LAFS already configured",
                "Tahoe-LAFS is already configured on this computer. "
                "Do you want to overwrite your existing configuration?")
            if reply == QMessageBox.Yes:
                shutil.rmtree(nodedir, ignore_errors=True)
            else:
                return
        self.invite_form = InviteForm()
        self.invite_form.show()
        self.invite_form.raise_()


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(SystemTrayIcon, self).__init__()
        self.parent = parent

        self.new_folder_window = NewFolderWindow(parent)
        self.preferences_window = PreferencesWindow()

        self.setIcon(QIcon(resource(settings['application']['tray_icon'])))

        self.right_menu = RightClickMenu(self)
        self.setContextMenu(self.right_menu)
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
            open_gridsync_folder()


def open_gridsync_folder():
    # XXX This should probably be removed...
    gridsync_folder = os.path.join(os.path.expanduser("~"), "Gridsync")
    if sys.platform == 'darwin':
        subprocess.Popen(['open', gridsync_folder])
    elif sys.platform == 'win32':
        subprocess.Popen(['start', gridsync_folder], shell=True)
    else:
        subprocess.Popen(['xdg-open', gridsync_folder])


def open_online_documentation():
    webbrowser.open('https://github.com/gridsync/gridsync/wiki')


def open_github_issues():
    webbrowser.open('https://github.com/gridsync/gridsync/issues')
