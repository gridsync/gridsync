# -*- coding: utf-8 -*-

from typing import Optional

from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAction,
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from gridsync import APP_NAME, DEFAULT_AUTOSTART, features, resource
from gridsync.desktop import (
    autostart_disable,
    autostart_enable,
    autostart_is_enabled,
)
from gridsync.gui.widgets import VSpacer
from gridsync.msg import question
from gridsync.preferences import Preferences


class GeneralPane(QWidget):
    def __init__(self, preferences: Preferences):
        super().__init__()
        self.preferences = preferences

        startup_groupbox = QGroupBox("Startup:", self)
        self.checkbox_autostart = QCheckBox("Start automatically on login")
        self.checkbox_minimize = QCheckBox("Start minimized")

        startup_layout = QGridLayout()
        startup_layout.addWidget(self.checkbox_autostart)
        startup_layout.addWidget(self.checkbox_minimize)
        startup_groupbox.setLayout(startup_layout)

        layout = QGridLayout(self)
        layout.addWidget(startup_groupbox)
        layout.addItem(VSpacer())

        self.checkbox_minimize.stateChanged.connect(
            self.on_checkbox_minimize_changed
        )
        self.checkbox_autostart.stateChanged.connect(
            self.on_checkbox_autostart_changed
        )

        self.load_preferences()

    def load_preferences(self):
        if self.preferences.get("startup", "minimize") == "true":
            self.checkbox_minimize.setCheckState(Qt.Checked)
        else:
            self.checkbox_minimize.setCheckState(Qt.Unchecked)
        if autostart_is_enabled():
            self.checkbox_autostart.setCheckState(Qt.Checked)
        else:
            self.checkbox_autostart.setCheckState(Qt.Unchecked)

    def on_checkbox_minimize_changed(self, state):
        if state:
            self.preferences.set("startup", "minimize", "true")
        else:
            self.preferences.set("startup", "minimize", "false")

    def on_checkbox_autostart_changed(self, state):
        if DEFAULT_AUTOSTART and not state:
            if question(
                self,
                "Are you sure you wish to disable autostart?",
                f"{APP_NAME} will only update and renew folders while it is "
                f"running. Failing to launch {APP_NAME} for extended periods "
                "of time may result in data-loss.",
            ):
                autostart_disable()
            else:
                self.checkbox_autostart.setCheckState(Qt.Checked)
        elif state:
            autostart_enable()
        else:
            autostart_disable()


class NotificationsPane(QWidget):
    def __init__(self, preferences: Preferences):
        super().__init__()
        self.preferences = preferences

        notifications_groupbox = QGroupBox("Notifications:", self)
        notifications_label = QLabel("Show a desktop notification when...")
        self.checkbox_connection = QCheckBox("Connection status changes")
        self.checkbox_folder = QCheckBox("A folder is updated")
        self.checkbox_invite = QCheckBox("An invite code is used")
        if not features.invites and not features.grid_invites:
            self.checkbox_invite.setVisible(False)

        notifications_layout = QGridLayout()
        notifications_layout.addWidget(notifications_label)
        notifications_layout.addWidget(self.checkbox_folder)
        notifications_layout.addWidget(self.checkbox_invite)
        notifications_layout.addWidget(self.checkbox_connection)
        notifications_groupbox.setLayout(notifications_layout)

        layout = QGridLayout(self)
        layout.addWidget(notifications_groupbox)
        layout.addItem(VSpacer())

        self.checkbox_connection.stateChanged.connect(
            self.on_checkbox_connection_changed
        )
        self.checkbox_folder.stateChanged.connect(
            self.on_checkbox_folder_changed
        )
        self.checkbox_invite.stateChanged.connect(
            self.on_checkbox_invite_changed
        )

        self.load_preferences()

    def load_preferences(self):
        if self.preferences.get("notifications", "connection") == "true":
            self.checkbox_connection.setCheckState(Qt.Checked)
        else:
            self.checkbox_connection.setCheckState(Qt.Unchecked)
        if self.preferences.get("notifications", "folder") == "false":
            self.checkbox_folder.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_folder.setCheckState(Qt.Checked)
        if self.preferences.get("notifications", "invite") == "false":
            self.checkbox_invite.setCheckState(Qt.Unchecked)
        else:
            self.checkbox_invite.setCheckState(Qt.Checked)

    def on_checkbox_connection_changed(self, state):
        if state:
            self.preferences.set("notifications", "connection", "true")
        else:
            self.preferences.set("notifications", "connection", "false")

    def on_checkbox_folder_changed(self, state):
        if state:
            self.preferences.set("notifications", "folder", "true")
        else:
            self.preferences.set("notifications", "folder", "false")

    def on_checkbox_invite_changed(self, state):
        if state:
            self.preferences.set("notifications", "invite", "true")
        else:
            self.preferences.set("notifications", "invite", "false")


class PreferencesWindow(QMainWindow):
    def __init__(self, preferences: Optional[Preferences] = None):
        super().__init__()

        if preferences is None:
            preferences = Preferences()
        self.preferences = preferences

        self.setMinimumSize(500, 300)
        self.setUnifiedTitleAndToolBarOnMac(True)

        self.toolbar = self.addToolBar("")
        self.toolbar.setIconSize(QSize(36, 36))
        self.toolbar.setMovable(False)
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.general_button = QToolButton(self)
        self.general_button.setDefaultAction(
            QAction(QIcon(resource("preferences.png")), "General")
        )
        self.general_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.general_button.setCheckable(True)
        self.general_button.triggered.connect(self.on_general_button_clicked)

        self.notifications_button = QToolButton(self)
        self.notifications_button.setDefaultAction(
            QAction(QIcon(resource("notification.png")), "Notifications")
        )
        self.notifications_button.setToolButtonStyle(
            Qt.ToolButtonTextUnderIcon
        )
        self.notifications_button.setCheckable(True)
        self.notifications_button.triggered.connect(
            self.on_notifications_button_clicked
        )

        self.toolbar.addWidget(self.general_button)
        self.toolbar.addWidget(self.notifications_button)

        self.general_pane = GeneralPane(preferences)
        self.notifications_pane = NotificationsPane(preferences)

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
            "{} - Preferences - Notifications".format(APP_NAME)
        )
        self.notifications_button.setChecked(True)
        self.general_button.setChecked(False)
        self.stacked_widget.setCurrentWidget(self.notifications_pane)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
