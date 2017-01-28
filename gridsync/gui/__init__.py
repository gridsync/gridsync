# -*- coding: utf-8 -*-

import os
import shutil


from PyQt5.QtWidgets import QMessageBox

from gridsync import config_dir
from gridsync.gui.invite import InviteForm
from gridsync.gui.main_window import MainWindow
from gridsync.gui.systray import SystemTrayIcon
from gridsync.gui.wizard import Wizard


class Gui(object):
    def __init__(self, core):
        self.core = core
        self.invite_form = InviteForm()
        self.main_window = MainWindow(self)
        self.systray = SystemTrayIcon(self)
        self.wizard = Wizard(self)

    def show_message(self, title, message):
        self.systray.showMessage(title, message, msecs=5000)

    def show_invite_form(self):
        self.invite_form.show()
        self.invite_form.raise_()

    def show_main_window(self):
        self.main_window.show()
        self.main_window.raise_()

    def exec_wizard(self):
        self.wizard.exec_()

    def show(self):
        self.systray.show()
        self.show_main_window()

    def toggle(self):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.show_main_window()
