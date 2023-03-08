# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING, Optional

from qtpy.QtCore import QSize, Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAction,
    QComboBox,
    QMenu,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from gridsync import features, resource
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font

if TYPE_CHECKING:
    from gridsync.gui.main_window import (  # pylint: disable=cyclic-import
        MainWindow,
    )
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import


class ComboBox(QComboBox):
    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.setFont(Font(10))
        self.current_index = 0
        self.insertSeparator(0)
        self.addItem(" Add new...")

        self.activated.connect(self.on_activated)

    def on_activated(self, index: int) -> None:
        if index == self.count() - 1:  # If "Add new..." is selected
            self.setCurrentIndex(self.current_index)
        else:
            self.current_index = index
        gateway = self.currentData()
        logging.debug("Selected %s", gateway.name)

    def add_gateway(self, gateway: Tahoe) -> None:
        basename = os.path.basename(os.path.normpath(gateway.nodedir))
        icon = QIcon(os.path.join(gateway.nodedir, "icon"))
        if not icon.availableSizes():
            icon = QIcon(resource("tahoe-lafs.png"))
        self.insertItem(0, icon, basename, gateway)
        self.setCurrentIndex(0)
        self.current_index = 0

    def activate(self, name: str) -> None:
        for i in range(self.count()):
            if self.itemText(i) == name:
                self.setCurrentIndex(i)
                return


class FolderMenuButton(QToolButton):
    add_folder_triggered = Signal()
    join_folder_triggered = Signal()

    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        font = Font(8)

        self.action = QAction(
            QIcon(resource("folder-plus-outline.png")), "Add Folder", self
        )
        self.action.setEnabled(False)
        self.action.setToolTip("Add a Folder...")
        self.action.setFont(font)

        from_device_action = QAction(QIcon(), "From Local Device...", self)
        from_device_action.setToolTip("Add Folder from Local Device...")
        from_device_action.triggered.connect(self.add_folder_triggered)

        from_code_action = QAction(QIcon(), "From Invite Code...", self)
        from_code_action.setToolTip("Add Folder from Invite Code...")
        from_code_action.triggered.connect(self.join_folder_triggered)

        menu = QMenu(self)
        menu.addAction(from_device_action)
        menu.addAction(from_code_action)

        self.setDefaultAction(self.action)
        self.setFont(font)
        self.setMenu(menu)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet("QToolButton::menu-indicator { image: none }")


class AddFolderButton(QToolButton):
    add_folder_triggered = Signal()

    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        font = Font(8)

        self.action = QAction(
            QIcon(resource("folder-plus-outline.png")), "Add Folder", self
        )
        self.action.setEnabled(False)
        self.action.setToolTip("Add a Folder...")
        self.action.setFont(font)
        self.action.triggered.connect(lambda: print("OK"))  # XXX

        self.setDefaultAction(self.action)
        self.setFont(font)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet("QToolButton::menu-indicator { image: none }")

        self.pressed.connect(lambda: print("PRESSED"))  # XXX


class EnterCodeButton(QToolButton):
    enter_code_triggered = Signal()

    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        font = Font(8)

        self.action = QAction(
            QIcon(resource("invite.png")), "Enter Code", self
        )
        self.action.setToolTip("Enter an Invite Code...")
        self.action.setEnabled(False)
        self.action.setFont(font)
        self.action.triggered.connect(lambda: print("OK"))  # XXX

        self.setDefaultAction(self.action)
        self.setFont(font)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet("QToolButton::menu-indicator { image: none }")

        self.pressed.connect(lambda: print("PRESSED"))  # XXX


class InvitesMenuButton(QToolButton):
    enter_invite_action_triggered = Signal()
    create_invite_action_triggered = Signal()

    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        font = Font(8)

        self.action = QAction(QIcon(resource("invite.png")), "Invites", self)
        self.action.setToolTip("Enter or Create an Invite Code")
        self.action.setFont(font)
        self.action.setEnabled(False)

        enter_invite_action = QAction(QIcon(), "Enter Invite Code...", self)
        enter_invite_action.setToolTip("Enter an Invite Code...")
        enter_invite_action.triggered.connect(
            self.enter_invite_action_triggered
        )

        create_invite_action = QAction(QIcon(), "Create Invite Code...", self)
        create_invite_action.setToolTip("Create on Invite Code...")
        create_invite_action.triggered.connect(
            self.create_invite_action_triggered
        )

        menu = QMenu(self)
        menu.addAction(enter_invite_action)
        menu.addAction(create_invite_action)

        self.setDefaultAction(self.action)
        self.setFont(font)
        self.setMenu(menu)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setStyleSheet("QToolButton::menu-indicator { image: none }")


class RecoveryMenuButton(QToolButton):
    import_action_triggered = Signal()
    export_action_triggered = Signal()

    def __init__(self, parent: Optional[ToolBar] = None) -> None:
        super().__init__(parent)
        font = Font(8)

        self.action = QAction(
            QIcon(resource("key-outline.png")), "Recovery", self
        )
        self.action.setEnabled(False)
        self.action.setToolTip("Create or Restore from a Recovery Key")
        self.action.setFont(font)

        import_action = QAction(QIcon(), "Restore from Recovery Key...", self)
        import_action.setToolTip("Restore from Recovery Key...")
        import_action.triggered.connect(self.import_action_triggered.emit)

        export_action = QAction(QIcon(), "Create Recovery Key...", self)
        export_action.setToolTip("Create Recovery Key...")
        export_action.triggered.connect(self.export_action_triggered.emit)

        menu = QMenu(self)
        menu.addAction(import_action)
        menu.addAction(export_action)

        self.setDefaultAction(self.action)
        self.setFont(font)
        self.setMenu(menu)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setStyleSheet("QToolButton::menu-indicator { image: none }")
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)


class ToolBar(QToolBar):
    add_folder_triggered = Signal()
    join_folder_triggered = Signal()
    enter_invite_action_triggered = Signal()
    create_invite_action_triggered = Signal()
    import_action_triggered = Signal()
    export_action_triggered = Signal()
    folders_action_triggered = Signal()
    history_action_triggered = Signal()
    usage_action_triggered = Signal()

    def __init__(  # noqa: max-complexity
        self, main_window: MainWindow
    ) -> None:
        super().__init__(parent=main_window)
        self.main_window = main_window

        self.recovery_key_exporter = None

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

        self.folder_button = AddFolderButton(self)
        self.recovery_button = RecoveryMenuButton(self)

        if features.grid_invites:
            self.invites_button = InvitesMenuButton(self)
            self.invites_button.enter_invite_action_triggered.connect(
                self.enter_invite_action_triggered
            )
            self.invites_button.create_invite_action_triggered.connect(
                self.create_invite_action_triggered
            )
        elif features.invites:
            self.invites_button = EnterCodeButton(self)
            self.invites_button.pressed.connect(
                self.enter_invite_action_triggered
            )

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.combo_box = ComboBox(self)
        # self.combo_box.currentIndexChanged.connect(self.update_actions)
        if not features.multiple_grids:
            self.combo_box.hide()

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.history_action = QAction(
            QIcon(resource("clock-outline.png")), "History", self
        )
        self.history_action.setEnabled(False)
        self.history_action.setToolTip("Show/Hide History")
        self.history_action.setFont(font)
        self.history_action.setCheckable(True)

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

        self.usage_button = QToolButton(self)
        self.usage_button.setDefaultAction(self.usage_action)
        self.usage_button.setCheckable(True)
        self.usage_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.folder_wa = self.addWidget(self.folder_button)
        self.recovery_wa = self.addWidget(self.recovery_button)
        self.invites_wa = self.addWidget(self.invites_button)

        self.addWidget(spacer_left)
        self.addWidget(self.combo_box)
        self.addWidget(spacer_right)

        self.folders_wa = self.addWidget(self.folders_button)
        self.usage_wa = self.addWidget(self.usage_button)
        self.history_wa = self.addWidget(self.history_button)

        self.folder_button.add_folder_triggered.connect(  # XXX
            self.add_folder_triggered
        )
        try:
            self.folder_button.join_folder_triggered.connect(  # XXX
                self.join_folder_triggered
            )
        except AttributeError:
            pass
        self.recovery_button.import_action_triggered.connect(
            self.import_action_triggered
        )
        self.recovery_button.export_action_triggered.connect(
            self.export_action_triggered
        )
        self.history_button.clicked.connect(self.on_history_activated)
        self.folders_button.clicked.connect(self.on_folders_activated)
        self.usage_button.clicked.connect(self.on_usage_activated)

    def _update_action_visibility(self) -> None:
        gateway = self.combo_box.currentData()
        if not gateway:
            return
        if gateway.zkap_auth_required:
            self.usage_wa.setVisible(True)
            if features.grid_invites:
                self.invites_wa.setVisible(False)
            else:
                try:
                    # Suppress mypy error: "None" has no attribute "setVisible"
                    self.invite_wa.setVisible(False)  # type: ignore
                except AttributeError:
                    pass
        else:
            self.usage_wa.setVisible(False)
            if features.grid_invites:
                self.invites_wa.setVisible(True)
            else:
                try:
                    # Suppress mypy error: "None" has no attribute "setVisible"
                    self.invite_wa.setVisible(True)  # type: ignore
                except AttributeError:
                    pass

    def _maybe_enable_actions(self) -> None:  # noqa: max-complexity
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
            if features.grid_invites:
                self.invites_button.setEnabled(False)
            else:
                try:
                    self.invites_button.setEnabled(False)
                except AttributeError:
                    pass
            if not gateway.magic_folder.magic_folders:
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
            if features.grid_invites:
                self.invites_button.setEnabled(True)
            else:
                try:
                    self.invites_button.setEnabled(True)
                except AttributeError:
                    pass

    def update_actions(self) -> None:
        self._maybe_enable_actions()
        self._update_action_visibility()

    def on_folders_activated(self) -> None:
        self.folders_button.setChecked(True)
        self.usage_button.setChecked(False)
        self.history_button.setChecked(False)
        self.update_actions()
        self.folders_action_triggered.emit()

    def on_usage_activated(self) -> None:
        self.folders_button.setChecked(False)
        self.usage_button.setChecked(True)
        self.history_button.setChecked(False)
        self.update_actions()
        self.usage_action_triggered.emit()

    def on_history_activated(self) -> None:
        self.folders_button.setChecked(False)
        self.usage_button.setChecked(False)
        self.history_button.setChecked(True)
        self.update_actions()
        self.history_action_triggered.emit()
