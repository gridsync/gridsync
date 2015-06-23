from PyQt4.QtGui import *

import resources
import threading

from wizard import Wizard


class LeftClickMenu(QMenu):
    def __init__(self, parent):
        super(LeftClickMenu, self).__init__()

        icon = QIcon.fromTheme("document-new")
        self.addAction(QAction(icon, "&New", self))

        icon = QIcon("")
        start_action = QAction(icon, '&Start', self)
        start_action.triggered.connect(parent.start_animation)
        self.addAction(start_action)

        icon = QIcon("")
        stop_action = QAction(icon, '&Stop', self)
        stop_action.triggered.connect(parent.stop_animation)
        self.addAction(stop_action)


class RightClickMenu(QMenu):
    def __init__(self):
        super(RightClickMenu, self).__init__()

        icon = QIcon("")
        self.addAction(QAction(icon, "&Show main window", self))

        icon = QIcon("")
        wizard_action = QAction(icon, '&Wizard', self)
        wizard_action.triggered.connect(show_wizard)
        self.addAction(wizard_action)

        self.addSeparator()

        icon = QIcon("")
        quit_action = QAction(icon, '&Quit', self)
        quit_action.setShortcut('Ctrl+Q')
        quit_action.triggered.connect(qApp.quit)
        self.addAction(quit_action)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent):
        super(SystemTrayIcon, self).__init__()
        self.parent = parent
        self.setIcon(QIcon(":/images/icon.png"))

        self.right_menu = RightClickMenu()
        self.setContextMenu(self.right_menu)

        self.left_menu = LeftClickMenu(self)
        self.activated.connect(self.on_click)

        self.movie = QMovie()
        self.movie.setFileName(":/images/sync.gif")
        self.movie.setSpeed(100)
        self.movie.updated.connect(self.on_systray_update)
        self.movie.setCacheMode(True)
        self.paused = True
        self.start_animation()
        
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
            self.setIcon(QIcon(":/images/icon.png"))
        
    def on_systray_update(self):
        icon = self.movie.currentPixmap()
        self.setIcon(QIcon(icon))
        #if not self.paused:
        #    self.setIcon(QIcon(self.movie.currentPixmap()))
        #elif self.paused:
        #    return 
        #else:
        #    self.paused = True
        #    self.setIcon(QIcon(":/images/icon.png"))

    def on_click(self, value):
        if value == QSystemTrayIcon.Trigger:
            self.left_menu.exec_(QCursor.pos())

def show_wizard(self):
    w = Wizard()
    w.exec_()


