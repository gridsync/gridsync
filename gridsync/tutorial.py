# -*- coding: utf-8 -*-

import sys

from PyQt4 import QtGui, QtCore

import uri


class Tutorial(QtGui.QWizard):
    def __init__(self, parent):
        super(Wizard, self).__init__()
        self.parent = parent
        self.create_welcome_page()
        self.create_systray_page()
        self.create_configuration1_page()
        self.create_configuration2_page()
        self.create_finish_page()
        self.setWindowTitle("Gridsync - Welcome")
        self.finished.connect(self.finish)

    def finish(self):
        introducer, dircap = uri.parse_uri(self.gridsync_link)
        # XXX Temporary; for demo purposes only!
        default_settings = {
                'sync_targets': {
                    'Gridsync': ['testgrid', '~/Gridsync', dircap]
                    },
                'tahoe_nodes': {
                    "testgrid": {
                        "node": {
                            "web.port": "tcp:0:interface=127.0.0.1",
                            "nickname": "Anonymous"
                        },
                        "client": {
                            "shares.happy": "1",
                            "shares.total": "1",
                            "shares.needed": "1",
                            "introducer.furl": introducer
                        }
                    }
                }
            }
        self.parent.settings = default_settings

    def create_welcome_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("Welcome to Gridsync!")

        label = QtGui.QLabel('Gridsync is a Free Software application based on Tahoe-LAFS, the Least Authority File Store. It allows you to safely store all of your important files into a storage "grid" -- a distributed cluster of servers connected to the Internet.\n\nUnlike most other traditional "Cloud" services, any data stored by Gridsync is safe and secure by default; nobody can read or alter the files stored in your grid without your permission -- not even the owners of the servers that store them.')
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        
        self.addPage(page)


    def create_systray_page(self):
        page = QtGui.QWizardPage()
        img = QtGui.QLabel()
        pixmap = QtGui.QPixmap(":osx-tray.png")
        img.setPixmap(pixmap)

        label = QtGui.QLabel('Like many other popular applications, Gridsync runs in the background of your computer and works while you do. If you ever need to change your settings, you can do so by clicking the Gridsync icon in your system tray.')
        label.setWordWrap(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(img, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        layout.addWidget(label)
        page.setLayout(layout)
        self.addPage(page)










    def get_directory(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Select file')
        if fname:
            self.lbl.setText(fname)
        else:
            self.lbl.setText('No file selected')


    def create_configuration1_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("Gridsync configuration... in two easy steps")
        #page.setSubTitle("Please fill both fields.")

        label = QtGui.QLabel('<b>Step 1.</b> Paste a Gridsync link below:\n\n ')
        label.setWordWrap(True)

        #self.dir = str(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))

        gridsync_link = QtGui.QLineEdit("gridsync://cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@test.gridsync.io:46210/DIR2:ibj7kjosqazmynuw4psud7egcy:lfxy6bk2khhii37uworkw3utd42bgld3boftzzlrac5u7j3kvifq")
        self.gridsync_link = str(gridsync_link.text())
        
        warning_label = QtGui.QLabel('\n\n\n\nGridsync links (in the form "<i>gridsync://some_text</i>") are special addresses that point to a Tahoe-LAFS storage grid -- or to a specific folder available on a storage grid. By pasting a Gridsync link into the space above, you are informing Gridsync of a location that it can use to store your files.')
        warning_label.setWordWrap(True)
        warning_label.setFont(QtGui.QFont('', 10))


        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(gridsync_link)
        layout.addWidget(warning_label)
        
        page.setLayout(layout)
        self.addPage(page)


    def create_configuration2_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("Gridsync configuration... in two easy steps")
        #page.setSubTitle("Please fill both fields.")

        label = QtGui.QLabel('<b>Step 2.</b> Select a local folder:\n\n ')
        label.setWordWrap(True)

        #self.dir = str(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))

        btn = QtGui.QPushButton('Choose file', self)
        self.connect(btn, QtCore.SIGNAL('clicked()'), self.get_directory)
        
        
        warning_label = QtGui.QLabel('\n\n\n\nGridsync works by pairing directories on your computer with directories located on a storage grid. The folder you select here will be automatically synchronized with the address provided on the previous page.')
        warning_label.setWordWrap(True)
        warning_label.setFont(QtGui.QFont('', 10))


        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(btn)
        layout.addWidget(warning_label)


        page.setLayout(layout)
        self.addPage(page)



    def create_finish_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("That's it!")
        
        self.settings = self.gridsync_link
        text = 'By clicking <b>Finish</b> below, Gridsync will begin synchronizing your selected folder with your storage grid and will continue to keep your files in sync so long as it is running.'
        label = QtGui.QLabel(text)
        label.setWordWrap(True)
        
        img = QtGui.QLabel()
        pixmap = QtGui.QPixmap(":sync-complete.png")
        img.setPixmap(pixmap)

        warning_label = QtGui.QLabel('\n\n\n\nPlease note that, depending on how many files you have, your initial sync may take a while. When Gridsync is working, the system tray icon will animate and you will receive a desktop notification as soon as the process completes.')
        warning_label.setWordWrap(True)
        warning_label.setFont(QtGui.QFont('', 10))

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(img, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        layout.addWidget(warning_label)
        page.setLayout(layout)

        self.addPage(page)


    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, 'Message',
            "Gridsync has not yet been configured. Are you sure to quit?", QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore() 
