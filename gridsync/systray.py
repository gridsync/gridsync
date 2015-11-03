# -*- coding: utf-8 -*-

import logging
import os
import resources
import subprocess
import sys
import webbrowser

from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QAction, QMainWindow, QMenu, QSystemTrayIcon
from twisted.internet import reactor

from gridsync.forms.preferences import Ui_MainWindow as Preferences
from gridsync.newfolder import NewFolderWindow


class PreferencesWindow(QMainWindow):
    def __init__(self, parent=None):
        super(PreferencesWindow, self).__init__()
        self.ui = Preferences()
        self.ui.setupUi(self)


class RightClickMenu(QMenu):
    def __init__(self, parent):
        super(RightClickMenu, self).__init__()
        self.parent = parent
        self.populate()

    def populate(self):
        self.clear()
        logging.debug("(Re-)populating systray menu...")
        new_folder_action = QAction(QIcon(""), "Add New Sync Folder...", self)
        new_folder_action.triggered.connect(self.parent.new_folder_window.populate_combo_box)
        new_folder_action.triggered.connect(self.parent.new_folder_window.show)
        self.addAction(new_folder_action)

        #open_action = QAction(QIcon(""), "Open Gridsync Folder", self)
        #open_action.triggered.connect(open_gridsync_folder)
        #self.addAction(open_action)

        snapshots_action = QAction(QIcon(""), "Browse Snapshots...", self)
        #snapshots_action.setEnabled(False)
        self.addAction(snapshots_action)
                
        self.addSeparator()
        
        status_action = QAction(QIcon(""), self.parent.parent.status_text, self)
        status_action.setEnabled(False)
        self.addAction(status_action)
        
        pause_action = QAction(QIcon(""), "Pause Syncing", self)
        self.addAction(pause_action)

        self.addSeparator()
        
        preferences_action = QAction(QIcon(""), "Preferences...", self)
        preferences_action.triggered.connect(self.parent.preferences_window.show)
        self.addAction(preferences_action)

        help_menu = QMenu(self)
        help_menu.setTitle("Help")

        documentation_action = QAction(QIcon(""), "Online Documentation...", self)
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
        quit_action.triggered.connect(self.parent.on_quit)
        self.addAction(quit_action)

class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(SystemTrayIcon, self).__init__()
        self.parent = parent

        self.new_folder_window = NewFolderWindow(parent)
        self.preferences_window = PreferencesWindow()
        
        self.setIcon(QIcon(":gridsync.png"))

        self.right_menu = RightClickMenu(self)
        self.setContextMenu(self.right_menu)
        self.activated.connect(self.on_click)

        self.movie = QMovie()
        self.movie.setFileName(":sync.gif")
        self.movie.updated.connect(self.on_systray_update)
        self.movie.setCacheMode(True)
        self.paused = True
        #self.start_animation()
        
    # The paused state needs to be set manually since QMovie.MovieState 
    # always returns 0 for movies rendered off-screen. This may be a bug.
    # http://pyqt.sourceforge.net/Docs/PyQt4/qmovie.html#MovieState-enum
    def start_animation(self):
        self.setToolTip("Gridsync - Syncing...")
        if self.paused:
            self.movie.setPaused(False)
            self.paused = False

    def stop_animation(self):
        self.setToolTip("Gridsync")
        if not self.paused:
            self.movie.setPaused(True)
            self.paused = True
            self.setIcon(QIcon(":gridsync.png"))

    def on_systray_update(self):
        self.setIcon(QIcon(self.movie.currentPixmap()))
        #if not self.paused:
        #    self.setIcon(QIcon(self.movie.currentPixmap()))
        #elif self.paused:
        #    return 
        #else:
        #    self.paused = True
        #    self.setIcon(QIcon(":/images/icon.png"))

    def on_click(self, value):
        #self.right_menu.populate()
        if value == QSystemTrayIcon.Trigger:
            open_gridsync_folder()

    def on_quit(self):
        reactor.stop()


def open_gridsync_folder():
    # XXX This should probably be removed...
    gridsync_folder = os.path.join(os.path.expanduser("~"), "Gridsync")
    if sys.platform == 'darwin':
        subprocess.Popen(['open', gridsync_folder])
    elif sys.platform == 'win32':
        subprocess.Popen(['start', gridsync_folder], shell= True)
    else:
        subprocess.Popen(['xdg-open', gridsync_folder])

def open_online_documentation():
    webbrowser.open('https://github.com/gridsync/gridsync/wiki')

def open_github_issues():
    webbrowser.open('https://github.com/gridsync/gridsync/issues')
