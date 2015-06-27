#!/usr/bin/env python

from __future__ import unicode_literals

import sys

from PyQt4 import QtGui, QtCore


class Wizard(QtGui.QWizard):
    def __init__(self):
        super(Wizard, self).__init__()
        self.create_welcome_page()
        self.create_systray_page()
        self.createRegistrationPage()
        self.createConclusionPage()
        self.setWindowTitle("Gridsync - Welcome")

    def create_welcome_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("Welcome to Gridsync!")

        label = QtGui.QLabel('Gridsync is a Free Software application based on Tahoe-LAFS, the Least Authority File Store. It allows you to safely store all of your important files into a storage "grid" -- a distributed cluster of computers connected to the Internet.\n\nUnlike most other traditional "Cloud" services, any data stored by Gridsync is safe and secure by default; nobody can read or alter the files stored in your grid without your permission -- not even the owners of the computers that store them.')
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        
        self.addPage(page)


    def create_systray_page(self):
        page = QtGui.QWizardPage()
        #page.setTitle("Welcome to Gridsync!")
        label = QtGui.QLabel('[INSERT SYSTRAY IMAGE HERE]\n\n\nLike many other popular applications, Gridsync runs in the background of your computer and works while you do. If you ever need to change your settings, you can do so by clicking the Gridsync icon in your system tray.')
        label.setWordWrap(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        self.addPage(page)

    def create_configuration_page(self):
        page = QtGui.QWizardPage()
        #page.setTitle("Welcome to Gridsync!")
        label = QtGui.QLabel('To get started, please enter a Gridsync storage link below. If you don\'t have one, you can use the default "public test grid" temporarily.')
        label.setWordWrap(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        self.addPage(page)



    def createRegistrationPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Configuration")
        #page.setSubTitle("Please fill both fields.")
        label = QtGui.QLabel('To get started, please enter a Gridsync storage address below:\n')
        label.setWordWrap(True)

        gridsync_link = QtGui.QLineEdit("gridsync://cmrh3t4vselhwcrdzt56rgxlcw5s2zaz@test.gridsync.io:2045")
        self.gridsync_link = gridsync_link.text()
        
        warning_label = QtGui.QLabel('\n\n(If you do not have a Gridsync storage address, you may use the Gridsync project\'s "Public Test Grid" at the address specified above -- but be warned: as this grid is for testing purposes only, it may not always be online and there is no guarantee that your stored files will be available in the future; do not use this service to store anything important!)')
        warning_label.setWordWrap(True)
        #nameLabel = QtGui.QLabel("Gridsync storage address:")
        #gridsync_link = QtGui.QLineEdit("gridsync:MNWXE2BTOQ2HM43FNRUHOY3SMR5HINJWOJTXQ3DDO42XGMT2MF5EA5DFON2C4Z3SNFSHG6LOMMXGS3Z2GIYDINI")
        #emailLabel = QtGui.QLabel("Email address:")
        #emailLineEdit = QtGui.QLineEdit()

        layout = QtGui.QVBoxLayout()
        #layout = QtGui.QGridLayout()
        layout.addWidget(label)
        layout.addWidget(gridsync_link)
        layout.addWidget(warning_label)
        #layout.addWidget(nameLabel)

        #layout.addWidget(nameLabel, 1, 0)
        #layout.addWidget(gridsync_link, 1, 1)
        page.setLayout(layout)

        self.addPage(page)

    def createConclusionPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Conclusion")

        label = QtGui.QLabel(self.gridsync_link)
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
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

