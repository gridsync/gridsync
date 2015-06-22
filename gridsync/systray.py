from PyQt4.QtGui import *

import resources

from wizard import Wizard


class LeftClickMenu(QMenu):
    def __init__(self):
        super(LeftClickMenu, self).__init__()

        icon = QIcon.fromTheme("document-new")
        self.addAction(QAction(icon, "&New", self))


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
    def __init__(self):
        super(SystemTrayIcon, self).__init__()
        self.setIcon(QIcon(":/images/icon.png"))
        
        self.right_menu = RightClickMenu()
        self.setContextMenu(self.right_menu)

        self.left_menu = LeftClickMenu()

        self.activated.connect(self.on_click)

        self.movie = QMovie()
        self.movie.setFileName(":/images/sync.gif")
        self.movie.setSpeed(150)
        self.movie.updated.connect(self.on_systray_update)
        self.movie.start()

    def on_systray_update(self):
        icon = self.movie.currentPixmap()
        self.setIcon(QIcon(icon))
        #print('blah')

    def on_click(self, value):
        if value == QSystemTrayIcon.Trigger:
            #self.movie.stop()
            #self.setIcon(QIcon(":/images/icon.png"))
            #self.movie.stop()
            #if not self.movie.MovieState():
            #    self.movie.setPaused(True)
            #else:
            #    self.movie.setPaused(False)
            print(self.movie.MovieState())
            print(self.movie.currentFrameNumber())
            self.left_menu.exec_(QCursor.pos())


def show_wizard(self):
    w = Wizard()
    w.exec_()

