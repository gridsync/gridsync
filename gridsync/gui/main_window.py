#!/usr/bin/env python

from __future__ import unicode_literals

import sys
#import signal

from systray import SystemTrayIcon

from PyQt4 import QtGui, QtCore


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        #self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Gridsync')
        #self.setWindowIcon(QtGui.QIcon('web.png'))        
        btn = QtGui.QPushButton('Button', self)
        btn.resize(btn.sizeHint())
        btn.move(50, 50)
        btn.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.show()
        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Quit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Quit')
        exitAction.triggered.connect(QtGui.qApp.quit)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)


def main():
    #signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtGui.QApplication(sys.argv)

    tray = SystemTrayIcon()
    tray.show()

    #mw = MainWindow()
    #mw.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

