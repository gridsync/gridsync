#!/usr/bin/env python

import sys
from PyQt4 import QtGui


class Example(QtGui.QWidget):
    
    def __init__(self):
        super(Example, self).__init__()
        
        #self.initUI()
        
        
    #def initUI(self):
        #self.setToolTip('This is a <b>QWidget</b> widget')    
        self.setGeometry(300, 300, 250, 150)
        #self.setWindowTitle('Icon')
        #self.setWindowIcon(QtGui.QIcon('web.png'))        
    
        btn = QtGui.QPushButton('Button', self)
        #btn.setToolTip('This is a <b>QPushButton</b> widget')
        btn.resize(btn.sizeHint())
        btn.move(50, 50)      

        self.show()
        
        
def main():
    
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()    
