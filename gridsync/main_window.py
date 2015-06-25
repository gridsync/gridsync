#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        #self.setGeometry(300, 300, 250, 150)
        self.setWindowTitle('Gridsync')
        #self.setWindowIcon(QtGui.QIcon('web.png'))        
        btn = QPushButton('Button', self)
        btn.resize(btn.sizeHint())
        btn.move(50, 50)
        btn.clicked.connect(QCoreApplication.instance().quit)
        self.show()
        exitAction = QAction(QIcon('exit.png'), '&Quit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Quit')
        exitAction.triggered.connect(qApp.quit)

        self.statusBar()

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())

