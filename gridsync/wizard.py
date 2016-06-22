# -*- coding: utf-8 -*-

import os
import sys

from PyQt5.QtWidgets import (
    QLabel, QMessageBox, QVBoxLayout, QWizard, QWizardPage)

from gridsync.widgets import GridSelector, FolderSelector


class WelcomePage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setTitle("Welcome to Gridsync!")

        label = QLabel(
            "Gridsync is an experimental desktop client for for Tahoe-LAFS, "
            "the Least Authority File Store. Unlike most traditional 'cloud' "
            "services, any data stored inside a Tahoe-LAFS storage grid is "
            "safe and secure by default; nobody can read or alter the files "
            "stored in a grid without your permission -- not even the owners "
            "of the computers that host them.\n\n"
            #If you already have an invite code "
            #"to join a grid, you can enter it on the following page. If not, "
            "This setup wizard will guide you through the process of "
            "selecting a storage grid so that you can begin to securely "
            "store and retrieve your files.")
        label.setWordWrap(True)

        #radio_1 = QRadioButton("I already have an invite code.")
        #radio_2 = QRadioButton("I do not have an invite code.")

        vbox = QVBoxLayout(self)
        vbox.addWidget(label)


class SelectGridPage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.introducer_furl = None

        self.grid_selector = GridSelector()

        help_text = QLabel(
            "A grid is a collection of computers that provide file storage "
            "services. In future versions, Gridsync will allow you to "
            "set up your own storage grid and invite others to join.")
        help_text.setWordWrap(True)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.grid_selector)
        vbox.addWidget(help_text)

    def validatePage(self):
        if self.grid_selector.introducer_furl:
            self.introducer_furl = self.grid_selector.introducer_furl
            return True
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Gridsync")
            msg.setText("Please select a storage grid.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return False


#class DriveSharePage(QWizardPage):
#    def __init__(self):
#	super(self.__class__, self).__init__()
#       self.drive_share = False


class SelectFolderPage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.folder = None
        default_path = os.path.join(os.path.expanduser('~'), 'Gridsync')

        self.folder_selector = FolderSelector()
        self.folder_selector.line_edit.setText(default_path)
        self.folder_selector.folder = default_path

        help_text = QLabel(
            "The folder you select will be securely backed up into the "
            "storage grid chosen on the previous page. In future versions, "
            "Gridsync will allow you to share folders with other users.")
        help_text.setWordWrap(True)

        vbox = QVBoxLayout(self)
        vbox.addWidget(self.folder_selector)
        vbox.addWidget(help_text)

    def validatePage(self):
        self.folder = self.folder_selector.folder
        if self.folder:
            return True
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Gridsync")
            msg.setText("Please select a folder.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return False


class FinishedPage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setTitle("Setup complete!")

        verb = ('Done' if sys.platform == 'darwin' else 'Finish')

        text = QLabel(
            "By clicking {} below, Gridsync will synchronize your selected "
            "folder with the storage grid and will continue to keep your "
            "files backed up so long as it is running.\n\nPlease note that, "
            "depending on how many files you have, your initial sync may "
            "take a while. Gridsync will notify you when this process "
            "has completed.".format(verb))
        text.setWordWrap(True)

        vbox = QVBoxLayout(self)
        vbox.addWidget(text)


class Wizard(QWizard):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setWindowTitle("Gridsync - Welcome")
        self.resize(800, 500)
        self.introducer_furl = None
        self.folder = None

        self.welcome_page = WelcomePage()
        self.select_grid_page = SelectGridPage()
        self.select_folder_page = SelectFolderPage()
        self.finished_page = FinishedPage()

        self.addPage(self.welcome_page)
        self.addPage(self.select_grid_page)
        self.addPage(self.select_folder_page)
        self.addPage(self.finished_page)

        self.finished.connect(self.finish)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Exit Gridsync setup?',
            "Gridsync has not yet been configured. "
            "Are you sure you wish to quit?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def finish(self):
        self.introducer_furl = self.select_grid_page.introducer_furl
        self.folder = self.select_folder_page.folder
