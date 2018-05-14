# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QCheckBox, QDialogButtonBox, QGridLayout, QGroupBox, QLabel, QSizePolicy,
    QSpacerItem, QWidget)
from gridsync.desktop import (
    autostart_enable, autostart_is_enabled, autostart_disable)
from gridsync.preferences import set_preference, get_preference


class PreferencesWidget(QWidget):

    accepted = pyqtSignal()

    def __init__(self, vertical_layout=False):
        super(PreferencesWidget, self).__init__()
        notifications_groupbox = QGroupBox("Notifications:", self)
        notifications_label = QLabel("Show a desktop notification when...")
        self.checkbox_connection = QCheckBox("Connection status changes")
        self.checkbox_folder = QCheckBox("A folder is updated")
        self.checkbox_invite = QCheckBox("An invite code is used")

        notifications_layout = QGridLayout()
        notifications_layout.addWidget(notifications_label)
        notifications_layout.addWidget(self.checkbox_connection)
        notifications_layout.addWidget(self.checkbox_folder)
        notifications_layout.addWidget(self.checkbox_invite)
        notifications_groupbox.setLayout(notifications_layout)

        startup_groupbox = QGroupBox("Startup:", self)
        self.checkbox_autostart = QCheckBox("Start automatically on login")
        self.checkbox_minimize = QCheckBox("Start minimized")
        startup_layout = QGridLayout()
        startup_layout.addWidget(self.checkbox_autostart)
        startup_layout.addWidget(self.checkbox_minimize)
        startup_groupbox.setLayout(startup_layout)

        # XXX Placeholder, for user-testing
        updates_groupbox = QGroupBox("Software Updates:", self)
        self.checkbox_updates_check = QCheckBox(
            "Check for updates automatically")
        self.checkbox_updates_install = QCheckBox(
            "Install updates automatically")
        updates_layout = QGridLayout()
        updates_layout.addWidget(self.checkbox_updates_check)
        updates_layout.addWidget(self.checkbox_updates_install)
        updates_groupbox.setLayout(updates_layout)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok)

        if vertical_layout:
            layout = QGridLayout(self)
            layout.addWidget(notifications_groupbox)
            layout.addWidget(startup_groupbox)
            layout.addWidget(updates_groupbox)
            layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
            layout.addWidget(self.buttonbox)
        else:
            layout = QGridLayout(self)
            layout.addWidget(notifications_groupbox, 1, 1, 1, 2)
            layout.addWidget(startup_groupbox, 2, 1)
            layout.addWidget(updates_groupbox, 2, 2)
            layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 3, 1)
            layout.addWidget(self.buttonbox, 4, 2)

        self.load_preferences()

        self.checkbox_connection.stateChanged.connect(
            self.on_checkbox_connection_changed)
        self.checkbox_folder.stateChanged.connect(
            self.on_checkbox_folder_changed)
        self.checkbox_invite.stateChanged.connect(
            self.on_checkbox_invite_changed)
        self.checkbox_minimize.stateChanged.connect(
            self.on_checkbox_minimize_changed)
        self.checkbox_autostart.stateChanged.connect(
            self.on_checkbox_autostart_changed)
        self.checkbox_updates_check.stateChanged.connect(
            self.on_checkbox_updates_check_changed)
        self.checkbox_updates_install.stateChanged.connect(
            self.on_checkbox_updates_install_changed)
        self.buttonbox.accepted.connect(self.accepted.emit)

    def load_preferences(self):
        if get_preference('notifications', 'connection') == 'false':
            self.checkbox_connection.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_connection.setCheckState(Qt.Checked)
        if get_preference('notifications', 'folder') == 'false':
            self.checkbox_folder.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_folder.setCheckState(Qt.Checked)
        if get_preference('notifications', 'invite') == 'false':
            self.checkbox_invite.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_invite.setCheckState(Qt.Checked)
        if get_preference('startup', 'minimize') == 'true':
            self.checkbox_minimize.setCheckState(Qt.Checked)
        else:
            self.checkbox_minimize.setCheckState(Qt.Unchecked)
        if autostart_is_enabled():
            self.checkbox_autostart.setCheckState(Qt.Checked)
        else:
            self.checkbox_autostart.setCheckState(Qt.Unchecked)
        if get_preference('updates', 'check') == 'true':
            self.checkbox_updates_check.setCheckState(Qt.Checked)
        else:
            self.checkbox_updates_check.setCheckState(Qt.Unchecked)
        if get_preference('updates', 'install') == 'true':
            self.checkbox_updates_install.setCheckState(Qt.Checked)
        else:
            self.checkbox_updates_install.setCheckState(Qt.Unchecked)

    def on_checkbox_connection_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'connection', 'true')
        else:
            set_preference('notifications', 'connection', 'false')

    def on_checkbox_folder_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'folder', 'true')
        else:
            set_preference('notifications', 'folder', 'false')

    def on_checkbox_invite_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('notifications', 'invite', 'true')
        else:
            set_preference('notifications', 'invite', 'false')

    def on_checkbox_minimize_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('startup', 'minimize', 'true')
        else:
            set_preference('startup', 'minimize', 'false')

    def on_checkbox_autostart_changed(self, state):  # pylint:disable=no-self-use
        if state:
            autostart_enable()
        else:
            autostart_disable()

    def on_checkbox_updates_check_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('updates', 'check', 'true')
        else:
            set_preference('updates', 'check', 'false')

    def on_checkbox_updates_install_changed(self, state):  # pylint:disable=no-self-use
        if state:
            set_preference('updates', 'install', 'true')
        else:
            set_preference('updates', 'install', 'false')
