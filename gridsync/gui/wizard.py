# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QGridLayout, QLabel, QMessageBox, QSizePolicy, QSpacerItem, QRadioButton,
    QWizard, QWizardPage)

from gridsync import settings
from gridsync.gui.invite import InviteForm
from gridsync.gui.widgets import GridSelector


class WelcomePage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setTitle("Welcome to {}!".format(settings['application']['name']))
        label = QLabel(
            "{} is a desktop client for Tahoe-LAFS, the Least Authority File "
            "Store. Unlike most traditional 'cloud' storage services, any "
            "data stored inside a Tahoe-LAFS storage grid is safe and secure "
            "by default; nobody can read or alter the files stored in a grid "
            "without your permission -- not even the owners of the storage "
            "nodes that comprise it.\n\n"
            "To get started, you will need to join a storage grid -- either "
            "by entering an invite code from a storage provider or by "
            "selecting a grid from a list of public providers.\n\n".format(
                settings['application']['name']))
        label.setWordWrap(True)

        self.radio_yes = QRadioButton(
            "I have an invite code from a storage provider")
        self.radio_no = QRadioButton(
            "I do not have an invite code and would like to use a public "
            "storage grid.")

        layout = QGridLayout(self)
        layout.addWidget(label, 1, 1, 1, 3)
        #layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 2, 1)
        layout.addWidget(self.radio_yes, 3, 2, 1, 1)
        layout.addWidget(self.radio_no, 4, 2, 1, 1)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 5, 1)

    def validatePage(self):
        if self.radio_yes.isChecked() or self.radio_no.isChecked():
            return True
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(settings['application']['name'])
            msg.setText("Please choose an option.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return False

    def nextId(self):
        if self.radio_yes.isChecked():
            return 2
        else:
            return 3


class InviteCodePage(QWizardPage):
    def __init__(self, gui):
        super(self.__class__, self).__init__()
        self.gui = gui
        self.invite_form = InviteForm(self.gui)
        layout = QGridLayout(self)
        layout.addWidget(self.invite_form)

    def keyPressEvent(self, event):  # pylint: disable=no-self-use
        key = event.key()
        if key == Qt.Key_Escape:
            event.ignore()

    def nextId(self):  # pylint: disable=no-self-use
        return -1


class SelectGridPage(QWizardPage):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.introducer_furl = None

        self.grid_selector = GridSelector()

        help_text = QLabel(
            "A grid is a collection of computers that provide file storage "
            "services. In future versions, {} will allow you to set up your "
            "own storage grid and invite others to join.".format(
                settings['application']['name']))
        help_text.setWordWrap(True)

        #vbox = QVBoxLayout(self)
        #vbox.addWidget(self.grid_selector)
        #vbox.addWidget(help_text)

        layout = QGridLayout(self)
        layout.addWidget(self.grid_selector)
        #layout.addWidget(help_text)

    def validatePage(self):
        if self.grid_selector.introducer_furl:
            self.introducer_furl = self.grid_selector.introducer_furl
            # TODO: tahoe create-client, etc.
            return True
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(settings['application']['name'])
            msg.setText("Please select a storage grid.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return False

    def nextId(self):  # pylint: disable=no-self-use
        return -1


class Wizard(QWizard):
    def __init__(self, gui):
        super(self.__class__, self).__init__()
        self.gui = gui
        self.gateway = None
        self.setWindowTitle("{} - Welcome".format(
            settings['application']['name']))
        #self.resize(800, 500)
        self.resize(640, 480)

        self.welcome_page = WelcomePage()
        self.invite_code_page = InviteCodePage(self.gui)
        self.select_grid_page = SelectGridPage()

        self.setPage(1, self.welcome_page)
        self.setPage(2, self.invite_code_page)
        self.setPage(3, self.select_grid_page)

        self.finished.connect(self.on_finished)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "Exit {} setup?".format(settings['application']['name']),
            "{} has not yet been configured. Are you sure you wish to "
            "quit?".format(settings['application']['name']),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Escape:
            self.close()

    def on_finished(self):
        self.gateway = self.invite_code_page.invite_form.gateway
