# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QMenu,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from gridsync import resource, settings
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font


class ComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.setFont(Font(10))
        self.current_index = 0
        self.insertSeparator(0)
        self.addItem(" Add new...")

        self.activated.connect(self.on_activated)

    def on_activated(self, index):
        if index == self.count() - 1:  # If "Add new..." is selected
            self.setCurrentIndex(self.current_index)
        else:
            self.current_index = index
        gateway = self.currentData()
        logging.debug("Selected %s", gateway.name)

    def add_gateway(self, gateway):
        basename = os.path.basename(os.path.normpath(gateway.nodedir))
        icon = QIcon(os.path.join(gateway.nodedir, "icon"))
        if not icon.availableSizes():
            icon = QIcon(resource("tahoe-lafs.png"))
        self.insertItem(0, icon, basename, gateway)
        self.setCurrentIndex(0)
        self.current_index = 0


class ToolBar(QToolBar):

    folder_action_triggered = Signal()
    enter_invite_action_triggered = Signal()
    create_invite_action_triggered = Signal()
    import_action_triggered = Signal()
    export_action_triggered = Signal()
    folders_action_triggered = Signal()
    history_action_triggered = Signal()
    usage_action_triggered = Signal()

    def __init__(self, main_window):
        super().__init__(parent=main_window)
        self.main_window = main_window

        self.recovery_key_exporter = None

        self.grid_invites_enabled: bool = True
        self.invites_enabled: bool = True
        self.multiple_grids_enabled: bool = True

        features_settings = settings.get("features")
        if features_settings:
            grid_invites = features_settings.get("grid_invites")
            if grid_invites and grid_invites.lower() == "false":
                self.grid_invites_enabled = False
            invites = features_settings.get("invites")
            if invites and invites.lower() == "false":
                self.invites_enabled = False
            multiple_grids = features_settings.get("multiple_grids")
            if multiple_grids and multiple_grids.lower() == "false":
                self.multiple_grids_enabled = False

        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color(), 0.7
        ).name()
        if sys.platform != "darwin":
            self.setStyleSheet(
                """
                QToolBar {{ border: 0px }}
                QToolButton {{ color: {} }}
            """.format(
                    dimmer_grey
                )
            )
        else:
            self.setStyleSheet(
                "QToolButton {{ color: {} }}".format(dimmer_grey)
            )
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(24, 24))
        self.setMovable(False)

        font = Font(8)

        self.folder_action = QAction(
            QIcon(resource("folder-plus-outline.png")), "Add Folder", self
        )
        self.folder_action.setEnabled(False)
        self.folder_action.setToolTip("Add a Folder...")
        self.folder_action.setFont(font)
        # self.folder_action.triggered.connect(self.select_folder)
        self.folder_action.triggered.connect(self.folder_action_triggered.emit)

        self.folder_button = QToolButton(self)
        self.folder_button.setDefaultAction(self.folder_action)
        self.folder_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        recovery_action = QAction(
            QIcon(resource("key-outline.png")), "Recovery", self
        )
        recovery_action.setEnabled(False)
        recovery_action.setToolTip("Import or Export a Recovery Key")
        recovery_action.setFont(font)

        self.import_action = QAction(QIcon(), "Import Recovery Key...", self)
        self.import_action.setToolTip("Import Recovery Key...")
        # import_action.triggered.connect(self.import_recovery_key)
        self.import_action.triggered.connect(self.import_action_triggered.emit)

        self.export_action = QAction(QIcon(), "Export Recovery Key...", self)
        self.export_action.setToolTip("Export Recovery Key...")
        # export_action.setShortcut(QKeySequence.Save)
        # export_action.triggered.connect(self.export_recovery_key)
        self.export_action.triggered.connect(self.export_action_triggered.emit)

        recovery_menu = QMenu(self)
        recovery_menu.addAction(self.import_action)
        recovery_menu.addAction(self.export_action)

        self.recovery_button = QToolButton(self)
        self.recovery_button.setDefaultAction(recovery_action)
        self.recovery_button.setMenu(recovery_menu)
        self.recovery_button.setPopupMode(2)
        self.recovery_button.setStyleSheet(
            "QToolButton::menu-indicator { image: none }"
        )
        self.recovery_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        if self.grid_invites_enabled:
            self.invites_action = QAction(
                QIcon(resource("invite.png")), "Invites", self
            )
            self.invites_action.setEnabled(False)
            self.invites_action.setToolTip("Enter or Create an Invite Code")
            self.invites_action.setFont(font)

            self.enter_invite_action = QAction(
                QIcon(), "Enter Invite Code...", self
            )
            self.enter_invite_action.setToolTip("Enter an Invite Code...")
            # self.enter_invite_action.triggered.connect(
            #    self.open_invite_receiver
            # )
            self.enter_invite_action.triggered.connect(
                self.enter_invite_action_triggered.emit
            )

            self.create_invite_action = QAction(
                QIcon(), "Create Invite Code...", self
            )
            self.create_invite_action.setToolTip("Create on Invite Code...")
            # self.create_invite_action.triggered.connect(
            #    self.open_invite_sender_dialog
            # )
            self.create_invite_action.triggered.connect(
                self.import_action_triggered.emit
            )

            self.invites_menu = QMenu(self)
            self.invites_menu.addAction(self.enter_invite_action)
            self.invites_menu.addAction(self.create_invite_action)

            self.invites_button = QToolButton(self)
            self.invites_button.setDefaultAction(self.invites_action)
            self.invites_button.setMenu(self.invites_menu)
            self.invites_button.setPopupMode(2)
            self.invites_button.setStyleSheet(
                "QToolButton::menu-indicator { image: none }"
            )
            self.invites_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        elif self.invites_enabled:
            self.invite_action = QAction(
                QIcon(resource("invite.png")), "Enter Code", self
            )
            self.invite_action.setEnabled(False)
            self.invite_action.setToolTip("Enter an Invite Code...")
            self.invite_action.setFont(font)
            # self.invite_action.triggered.connect(self.open_invite_receiver)
            self.invite_action.triggered.connect(
                self.enter_invite_action_triggered.emit
            )

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        self.combo_box = ComboBox(self)
        # self.combo_box.currentIndexChanged.connect(self.update_actions)
        if not self.multiple_grids_enabled:
            self.combo_box.hide()

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        self.history_action = QAction(
            QIcon(resource("clock-outline.png")), "History", self
        )
        self.history_action.setEnabled(False)
        self.history_action.setToolTip("Show/Hide History")
        self.history_action.setFont(font)
        self.history_action.setCheckable(True)
        # self.history_action.triggered.connect(self.show_history_view)
        self.history_action.triggered.connect(self.on_history_activated)

        self.history_button = QToolButton(self)
        self.history_button.setDefaultAction(self.history_action)
        self.history_button.setCheckable(True)
        self.history_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.folders_action = QAction(
            QIcon(resource("folder-multiple-outline.png")), "Folders", self
        )

        self.folders_action.setEnabled(False)
        self.folders_action.setToolTip("Show Folders")
        self.folders_action.setFont(font)
        self.folders_action.setCheckable(True)
        # self.folders_action.triggered.connect(self.show_folders_view)
        self.folders_action.triggered.connect(self.on_folders_activated)

        self.folders_button = QToolButton(self)
        self.folders_button.setDefaultAction(self.folders_action)
        self.folders_button.setCheckable(True)
        self.folders_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.usage_action = QAction(
            QIcon(resource("chart-donut.png")), "Storage-time", self
        )
        self.usage_action.setEnabled(False)
        self.usage_action.setToolTip("Show Storage-time")
        self.usage_action.setFont(font)
        self.usage_action.setCheckable(True)
        # self.usage_action.triggered.connect(self.show_usage_view)
        self.usage_action.triggered.connect(self.on_usage_activated)

        self.usage_button = QToolButton(self)
        self.usage_button.setDefaultAction(self.usage_action)
        self.usage_button.setCheckable(True)
        self.usage_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.folder_wa = self.addWidget(self.folder_button)
        self.recovery_wa = self.addWidget(self.recovery_button)
        if self.grid_invites_enabled:
            self.invites_wa = self.addWidget(self.invites_button)
        elif self.invites_enabled:
            self.invite_wa = self.addAction(self.invite_action)

        self.addWidget(spacer_left)
        self.addWidget(self.combo_box)
        self.addWidget(spacer_right)

        self.folders_wa = self.addWidget(self.folders_button)
        self.usage_wa = self.addWidget(self.usage_button)
        self.history_wa = self.addWidget(self.history_button)

    def _update_action_visibility(self):
        gateway = self.combo_box.currentData()
        if not gateway:
            return
        if gateway.zkap_auth_required:
            self.usage_wa.setVisible(True)
            if self.grid_invites_enabled:
                self.invites_wa.setVisible(False)
            else:
                try:
                    self.invite_wa.setVisible(False)
                except AttributeError:
                    pass
        else:
            self.usage_wa.setVisible(False)
            if self.grid_invites_enabled:
                self.invites_wa.setVisible(True)
            else:
                try:
                    self.invite_wa.setVisible(True)
                except AttributeError:
                    pass

    def _maybe_enable_actions(self):
        gateway = self.combo_box.currentData()
        if not gateway:
            return
        if (
            gateway.zkap_auth_required
            and not gateway.monitor.zkap_checker.zkaps_remaining
        ):
            self.folder_button.setEnabled(False)
            self.recovery_button.setEnabled(False)
            self.history_button.setEnabled(False)
            self.folders_button.setEnabled(False)
            self.usage_button.setEnabled(False)
            if self.grid_invites_enabled:
                self.invites_button.setEnabled(False)
            else:
                try:
                    self.invite_action.setEnabled(False)
                except AttributeError:
                    pass
            if not gateway.magic_folders:
                try:
                    self.main_window.central_widget.setCurrentWidget(  # XXX
                        self.main_window.central_widget.usage_views[gateway]
                    )
                except KeyError:
                    return
                self.usage_button.setChecked(True)
                self.history_button.setChecked(False)
                self.folders_button.setChecked(False)
        else:
            self.folder_button.setEnabled(True)
            self.recovery_button.setEnabled(True)
            self.history_button.setEnabled(True)
            self.folders_button.setEnabled(True)
            self.usage_button.setEnabled(True)
            if self.grid_invites_enabled:
                self.invites_button.setEnabled(True)
            else:
                try:
                    self.invite_action.setEnabled(True)
                except AttributeError:
                    pass

    def update_actions(self):
        self._maybe_enable_actions()
        self._update_action_visibility()

    def on_folders_activated(self):
        self.folders_button.setChecked(True)
        self.usage_button.setChecked(False)
        self.history_button.setChecked(False)
        self.update_actions()
        self.folders_action_triggered.emit()

    def on_usage_activated(self):
        self.folders_button.setChecked(False)
        self.usage_button.setChecked(True)
        self.history_button.setChecked(False)
        self.update_actions()
        self.usage_action_triggered.emit()

    def on_history_activated(self):
        self.folders_button.setChecked(False)
        self.usage_button.setChecked(False)
        self.history_button.setChecked(True)
        self.update_actions()
        self.history_action_triggered.emit()
