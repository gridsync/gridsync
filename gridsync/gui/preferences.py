# -*- coding: utf-8 -*-

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction, QCheckBox, QGridLayout, QGroupBox, QLabel, QMainWindow,
    QSizePolicy, QSpacerItem, QStackedWidget, QToolButton, QWidget)

from gridsync import APP_NAME, resource
from gridsync.desktop import (
    autostart_enable, autostart_is_enabled, autostart_disable)
from gridsync.preferences import set_preference, get_preference


class GeneralPane(QWidget):
    def __init__(self):
        super(GeneralPane, self).__init__()
        startup_groupbox = QGroupBox("Startup:", self)
        self.checkbox_autostart = QCheckBox("Start automatically on login")
        self.checkbox_minimize = QCheckBox("Start minimized")

        startup_layout = QGridLayout()
        startup_layout.addWidget(self.checkbox_autostart)
        startup_layout.addWidget(self.checkbox_minimize)
        startup_groupbox.setLayout(startup_layout)

        layout = QGridLayout(self)
        layout.addWidget(startup_groupbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))

        self.checkbox_minimize.stateChanged.connect(
            self.on_checkbox_minimize_changed)
        self.checkbox_autostart.stateChanged.connect(
            self.on_checkbox_autostart_changed)

        self.load_preferences()

    def load_preferences(self):
        if get_preference('startup', 'minimize') == 'true':
            self.checkbox_minimize.setCheckState(Qt.Checked)
        else:
            self.checkbox_minimize.setCheckState(Qt.Unchecked)
        if autostart_is_enabled():
            self.checkbox_autostart.setCheckState(Qt.Checked)
        else:
            self.checkbox_autostart.setCheckState(Qt.Unchecked)

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


class NotificationsPane(QWidget):
    def __init__(self):
        super(NotificationsPane, self).__init__()
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

        layout = QGridLayout(self)
        layout.addWidget(notifications_groupbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))

        self.checkbox_connection.stateChanged.connect(
            self.on_checkbox_connection_changed)
        self.checkbox_folder.stateChanged.connect(
            self.on_checkbox_folder_changed)
        self.checkbox_invite.stateChanged.connect(
            self.on_checkbox_invite_changed)

        self.load_preferences()

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


class PreferencesWindow(QMainWindow):
    def __init__(self):
        super(PreferencesWindow, self).__init__()
        self.setMinimumSize(500, 300)
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.toolbar = self.addToolBar('')
        self.toolbar.setIconSize(QSize(36, 36))
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.general_button = QToolButton(self)
        self.general_button.setDefaultAction(
            QAction(QIcon(resource('preferences.png')), "General"))
        self.general_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.general_button.setCheckable(True)
        self.general_button.triggered.connect(self.on_general_button_clicked)

        self.notifications_button = QToolButton(self)
        self.notifications_button.setDefaultAction(
            QAction(QIcon(resource('notification.png')), "Notifications"))
        self.notifications_button.setToolButtonStyle(
            Qt.ToolButtonTextUnderIcon)
        self.notifications_button.setCheckable(True)
        self.notifications_button.triggered.connect(
            self.on_notifications_button_clicked)

        self.toolbar.addWidget(self.general_button)
        self.toolbar.addWidget(self.notifications_button)

        self.general_pane = GeneralPane()
        self.notifications_pane = NotificationsPane()

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.general_pane)
        self.stacked_widget.addWidget(self.notifications_pane)
        self.setCentralWidget(self.stacked_widget)

        self.on_general_button_clicked()

    def on_general_button_clicked(self):
        self.setWindowTitle("{} - Preferences - General".format(APP_NAME))
        self.general_button.setChecked(True)
        self.notifications_button.setChecked(False)
        self.stacked_widget.setCurrentWidget(self.general_pane)

    def on_notifications_button_clicked(self):
        self.setWindowTitle(
            "{} - Preferences - Notifications".format(APP_NAME))
        self.notifications_button.setChecked(True)
        self.general_button.setChecked(False)
        self.stacked_widget.setCurrentWidget(self.notifications_pane)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
