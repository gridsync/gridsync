# -*- coding: utf-8 -*-

import sys
import resources
import logging

from PyQt4.QtGui import *

from gui.grid_editor import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)


class LeftClickMenu(QMenu):
    def __init__(self, parent):
        super(LeftClickMenu, self).__init__()


class RightClickMenu(QMenu):
    def __init__(self, parent):
        super(RightClickMenu, self).__init__()
        self.parent = parent

        icon = QIcon("")
        mw_action = QAction(icon, "Preferences", self)
        mw_action.triggered.connect(parent.mw.show)
        self.addAction(mw_action)

        self.addSeparator()
        # Help
        # --Online documentation...
        # --GitHub Issues...
        # -----
        # --About Gridsync

        icon = QIcon("")
        quit_action = QAction(icon, '&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(self.parent.on_quit)
        self.addAction(quit_action)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(SystemTrayIcon, self).__init__()
        self.parent = parent
        
        self.mw = MainWindow()
        
        self.setIcon(QIcon(":gridsync.png"))

        self.right_menu = RightClickMenu(self)
        self.setContextMenu(self.right_menu)

        self.left_menu = LeftClickMenu(self)
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
        if self.paused:
            self.movie.setPaused(False)
            self.paused = False

    def stop_animation(self):
        if not self.paused:
            self.movie.setPaused(True)
            self.paused = True
            self.setIcon(QIcon(":gridsync.png"))
            self.show_message('Gridsync', 'Synchronization complete.')
    
    def show_message(self, title, text):
        self.showMessage(title, text)

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
        if value == QSystemTrayIcon.Trigger:
            self.mw.show()
            #self.left_menu.exec_(QCursor.pos())

    def on_quit(self):
        self.parent.stop()
