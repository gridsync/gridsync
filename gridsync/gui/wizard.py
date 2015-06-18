#!/usr/bin/env python

from __future__ import unicode_literals

import sys

from PyQt4 import QtGui, QtCore


class Wizard(QtGui.QWizard):
    def __init__(self):
        super(Wizard, self).__init__()
        self.create_welcome_page()
        self.createRegistrationPage()
        self.createConclusionPage()
        self.setWindowTitle("Gridsync - Setup")

    def create_welcome_page(self):
        page = QtGui.QWizardPage()
        page.setTitle("Welcome!")

        label = QtGui.QLabel("This wizard will..")
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        
        self.addPage(page)

    def createRegistrationPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Registration")
        page.setSubTitle("Please fill both fields.")

        nameLabel = QtGui.QLabel("Name:")
        nameLineEdit = QtGui.QLineEdit()

        emailLabel = QtGui.QLabel("Email address:")
        emailLineEdit = QtGui.QLineEdit()

        layout = QtGui.QGridLayout()
        layout.addWidget(nameLabel, 0, 0)
        layout.addWidget(nameLineEdit, 0, 1)
        layout.addWidget(emailLabel, 1, 0)
        layout.addWidget(emailLineEdit, 1, 1)
        page.setLayout(layout)

        self.addPage(page)

    def createConclusionPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Conclusion")

        label = QtGui.QLabel("Have a nice day!")
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

