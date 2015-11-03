# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtGui import QFont, QPixmap 
from PyQt5.QtWidgets import (QLabel, QHBoxLayout, QVBoxLayout, QLineEdit, 
        QPushButton, QWidget, QWizard, QWizardPage)

from gridsync.tahoe import DEFAULT_SETTINGS


class Tutorial(QWizard):
    def __init__(self, parent):
        super(Tutorial, self).__init__()
        self.parent = parent
        self.create_welcome_page()
        self.create_systray_page()
        self.create_configuration1_page()
        self.create_configuration2_page()
        self.create_finish_page()
        self.selected_folder = ''
        self.setWindowTitle("Gridsync - Welcome")
        self.finished.connect(self.finish)

    def finish(self):
        settings = { 'Gridsync Demo': DEFAULT_SETTINGS }
        introducer_furl = str(self.introducer_furl.text())
        settings['Gridsync Demo']['client']['introducer.furl'] = introducer_furl
        settings['Gridsync Demo']['sync'][self.selected_folder] = None
        #logging.info("First run - Selected folder: " % str(self.selected_folder))
        logging.info(settings)
        self.parent.settings = settings

    def create_welcome_page(self):
        page = QWizardPage()
        page.setTitle("Welcome to Gridsync!")

        label = QLabel('Gridsync is an experimental desktop client for for Tahoe-LAFS, the Least Authority File Store. Tahoe-LAFS allows you to safely store all of your important files into a storage "grid" -- a distributed cluster of servers connected to the Internet.\n\nUnlike most other traditional "Cloud" services, any data stored by Tahoe-LAFS is safe and secure by default; nobody can read or alter the files stored in your grid without your permission -- not even the owners of the servers that store them.')
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)
        
        self.addPage(page)


    def create_systray_page(self):
        page = QWizardPage()
        img = QLabel()
        pixmap = QPixmap(":osx-prefs.png")
        img.setPixmap(pixmap)

        label = QLabel('Like many other popular applications, Gridsync runs in the background of your computer and works while you do. If you ever need to change your settings in the future, you can do so by clicking the Gridsync icon in your system tray.')
        label.setWordWrap(True)
        layout = QVBoxLayout()
        layout.addWidget(img)
        layout.addWidget(label)
        page.setLayout(layout)
        self.addPage(page)


    def get_folder(self):
        self.folder = QFileDialog.getExistingDirectory(
                self, "Select local folder to sync")
        if self.folder:
            self.folder_text.setText(self.folder)
            self.selected_folder = str(self.folder)


    def create_configuration1_page(self):
        page = QWizardPage()
        page.setTitle("Gridsync configuration... in two easy steps")

        label = QLabel('<b>Step 1.</b> Paste a Tahoe-LAFS Introducer fURL below:\n\n ')
        label.setWordWrap(True)

        self.introducer_furl = QLineEdit("")
        
        info_label = QLabel('\n\n\n\nAn "Introducer fURL" (in the form "<i>pb://nodeid@example.org/introducer</i>") is a special address that points to a Tahoe-LAFS storage grid. If you do not have an Introducer fURL, you can get one from the operator of a storage grid -- or from one of your friends that uses Tahoe-LAFS.')
        info_label.setWordWrap(True)
        info_label.setFont(QFont('', 10))


        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(self.introducer_furl)
        layout.addWidget(info_label)
        
        page.setLayout(layout)
        self.addPage(page)


    def create_configuration2_page(self):
        page = QWizardPage()
        page.setTitle("Gridsync configuration... in two easy steps")

        label = QLabel('<b>Step 2.</b> Select a local folder:\n\n ')
        label.setWordWrap(True)

        hbox = QWidget(self)
        hlayout = QHBoxLayout(hbox)
        self.folder_text = QLineEdit(hbox)
        button = QPushButton('Select Folder', self)
        button.clicked.connect(self.get_folder)
        hlayout.addWidget(self.folder_text)
        hlayout.addWidget(button)
        #self.folder_label = QLabel()
        
        warning_label = QLabel('\n\n\n\nGridsync works by pairing directories on your computer with directories located on a storage grid. The folder you select here will be automatically synchronized with the address provided on the previous page.')
        warning_label.setWordWrap(True)
        warning_label.setFont(QFont('', 10))


        layout = QVBoxLayout()
        layout.addWidget(label)
        #layout.addWidget(button)
        layout.addWidget(hbox)
        layout.addWidget(warning_label)


        page.setLayout(layout)
        self.addPage(page)

    def create_finish_page(self):
        page = QWizardPage()
        page.setTitle("That's it!")
        
        #self.settings = self.gridsync_link
        text = 'By clicking <b>Done</b> below, Gridsync will begin synchronizing your selected folder with your storage grid and will continue to keep your files in sync so long as it is running.'
        label = QLabel(text)
        label.setWordWrap(True)
        
        img = QLabel()
        pixmap = QPixmap(":sync-complete.png")
        img.setPixmap(pixmap)

        warning_label = QLabel('\n\n\n\nPlease note that, depending on how many files you have, your initial sync may take a while. When Gridsync is working, the system tray icon will animate and you will receive a desktop notification as soon as the process completes.')
        warning_label.setWordWrap(True)
        warning_label.setFont(QFont('', 10))

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addWidget(img)
        layout.addWidget(warning_label)
        page.setLayout(layout)

        self.addPage(page)


    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message',
            "Gridsync has not yet been configured. Are you sure you wish to quit?", QMessageBox.Yes | 
            QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore() 
