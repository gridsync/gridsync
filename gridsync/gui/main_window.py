# -*- coding: utf-8 -*-

import logging
import os
import sys

from PyQt5.QtCore import QItemSelectionModel, QFileInfo, QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QFileIconProvider,
    QGridLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QShortcut,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QWidget,
)
from twisted.internet import reactor

from gridsync import resource, APP_NAME, config_dir, settings
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.history import HistoryView
from gridsync.gui.pixmap import CompositePixmap
from gridsync.gui.share import InviteReceiverDialog, InviteSenderDialog
from gridsync.gui.status import StatusPanel
from gridsync.gui.view import View
from gridsync.gui.welcome import WelcomeDialog
from gridsync.msg import error, info
from gridsync.recovery import RecoveryKeyExporter
from gridsync.util import strip_html_tags


class ComboBox(QComboBox):
    def __init__(self):
        super(ComboBox, self).__init__()
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

    def add_gateway(self, gateway):
        basename = os.path.basename(os.path.normpath(gateway.nodedir))
        icon = QIcon(os.path.join(gateway.nodedir, "icon"))
        if not icon.availableSizes():
            icon = QIcon(resource("tahoe-lafs.png"))
        self.insertItem(0, icon, basename, gateway)
        self.setCurrentIndex(0)
        self.current_index = 0


class CentralWidget(QStackedWidget):
    def __init__(self, gui):
        super(CentralWidget, self).__init__()
        self.gui = gui
        self.views = []
        self.folders_views = {}
        self.history_views = {}

    def add_folders_view(self, gateway):
        view = View(self.gui, gateway)
        widget = QWidget()
        layout = QGridLayout(widget)
        if sys.platform == "darwin":
            # XXX: For some reason, getContentsMargins returns 20 px on macOS..
            layout.setContentsMargins(11, 11, 11, 0)
        else:
            left, _, right, _ = layout.getContentsMargins()
            layout.setContentsMargins(left, 0, right, 0)
        layout.addWidget(view)
        layout.addWidget(StatusPanel(gateway, self.gui))
        self.addWidget(widget)
        self.views.append(view)
        self.folders_views[gateway] = widget

    def add_history_view(self, gateway):
        view = HistoryView(gateway, self.gui)
        self.addWidget(view)
        self.history_views[gateway] = view


class MainWindow(QMainWindow):
    def __init__(self, gui):  # noqa: max-complexity
        super(MainWindow, self).__init__()
        self.gui = gui
        self.gateways = []
        self.welcome_dialog = None
        self.recovery_key_exporter = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(QSize(600, 400))
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.setContextMenuPolicy(Qt.NoContextMenu)

        if sys.platform == "darwin":
            # To disable the broken/buggy "full screen" mode on macOS.
            # See https://github.com/gridsync/gridsync/issues/241
            self.setWindowFlags(Qt.Dialog)

        grid_invites_enabled = True
        invites_enabled = True
        multiple_grids_enabled = True
        features_settings = settings.get("features")
        if features_settings:
            grid_invites = features_settings.get("grid_invites")
            if grid_invites and grid_invites.lower() == "false":
                grid_invites_enabled = False
            invites = features_settings.get("invites")
            if invites and invites.lower() == "false":
                invites_enabled = False
            multiple_grids = features_settings.get("multiple_grids")
            if multiple_grids and multiple_grids.lower() == "false":
                multiple_grids_enabled = False

        if multiple_grids_enabled:
            self.shortcut_new = QShortcut(QKeySequence.New, self)
            self.shortcut_new.activated.connect(self.show_welcome_dialog)

        self.shortcut_open = QShortcut(QKeySequence.Open, self)
        self.shortcut_open.activated.connect(self.select_folder)

        self.shortcut_preferences = QShortcut(QKeySequence.Preferences, self)
        self.shortcut_preferences.activated.connect(
            self.gui.show_preferences_window
        )

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.confirm_quit)

        self.central_widget = CentralWidget(self.gui)
        self.setCentralWidget(self.central_widget)

        font = Font(8)

        folder_icon_default = QFileIconProvider().icon(QFileInfo(config_dir))
        folder_icon_composite = CompositePixmap(
            folder_icon_default.pixmap(256, 256), resource("green-plus.png")
        )
        folder_icon = QIcon(folder_icon_composite)

        folder_action = QAction(folder_icon, "Add Folder", self)
        folder_action.setToolTip("Add a Folder...")
        folder_action.setFont(font)
        folder_action.triggered.connect(self.select_folder)

        if grid_invites_enabled:
            invites_action = QAction(
                QIcon(resource("invite.png")), "Invites", self
            )
            invites_action.setToolTip("Enter or Create an Invite Code")
            invites_action.setFont(font)

            enter_invite_action = QAction(
                QIcon(), "Enter Invite Code...", self
            )
            enter_invite_action.setToolTip("Enter an Invite Code...")
            enter_invite_action.triggered.connect(self.open_invite_receiver)

            create_invite_action = QAction(
                QIcon(), "Create Invite Code...", self
            )
            create_invite_action.setToolTip("Create on Invite Code...")
            create_invite_action.triggered.connect(
                self.open_invite_sender_dialog
            )

            invites_menu = QMenu(self)
            invites_menu.addAction(enter_invite_action)
            invites_menu.addAction(create_invite_action)

            invites_button = QToolButton(self)
            invites_button.setDefaultAction(invites_action)
            invites_button.setMenu(invites_menu)
            invites_button.setPopupMode(2)
            invites_button.setStyleSheet(
                "QToolButton::menu-indicator { image: none }"
            )
            invites_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        elif invites_enabled:
            invite_action = QAction(
                QIcon(resource("invite.png")), "Enter Code", self
            )
            invite_action.setToolTip("Enter an Invite Code...")
            invite_action.setFont(font)
            invite_action.triggered.connect(self.open_invite_receiver)

        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Expanding, 0)

        self.combo_box = ComboBox()
        self.combo_box.currentIndexChanged.connect(self.on_grid_selected)
        if not multiple_grids_enabled:
            self.combo_box.hide()

        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Expanding, 0)

        history_action = QAction(QIcon(resource("time.png")), "History", self)
        history_action.setToolTip("Show/Hide History")
        history_action.setFont(font)
        history_action.triggered.connect(self.on_history_button_clicked)

        self.history_button = QToolButton(self)
        self.history_button.setDefaultAction(history_action)
        self.history_button.setCheckable(True)
        self.history_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        recovery_action = QAction(QIcon(resource("key.png")), "Recovery", self)
        recovery_action.setToolTip("Import or Export a Recovery Key")
        recovery_action.setFont(font)

        import_action = QAction(QIcon(), "Import Recovery Key...", self)
        import_action.setToolTip("Import Recovery Key...")
        import_action.triggered.connect(self.import_recovery_key)

        export_action = QAction(QIcon(), "Export Recovery Key...", self)
        export_action.setToolTip("Export Recovery Key...")
        export_action.setShortcut(QKeySequence.Save)
        export_action.triggered.connect(self.export_recovery_key)

        recovery_menu = QMenu(self)
        recovery_menu.addAction(import_action)
        recovery_menu.addAction(export_action)

        recovery_button = QToolButton(self)
        recovery_button.setDefaultAction(recovery_action)
        recovery_button.setMenu(recovery_menu)
        recovery_button.setPopupMode(2)
        recovery_button.setStyleSheet(
            "QToolButton::menu-indicator { image: none }"
        )
        recovery_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        self.toolbar = self.addToolBar("")
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color(), 0.7
        ).name()
        if sys.platform != "darwin":
            self.toolbar.setStyleSheet(
                """
                QToolBar {{ border: 0px }}
                QToolButton {{ color: {} }}
            """.format(
                    dimmer_grey
                )
            )
        else:
            self.toolbar.setStyleSheet(
                "QToolButton {{ color: {} }}".format(dimmer_grey)
            )
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setMovable(False)
        self.toolbar.addAction(folder_action)
        if grid_invites_enabled:
            self.toolbar.addWidget(invites_button)
        elif invites_enabled:
            self.toolbar.addAction(invite_action)
        self.toolbar.addWidget(spacer_left)
        self.toolbar.addWidget(self.combo_box)
        self.toolbar.addWidget(spacer_right)
        self.toolbar.addWidget(self.history_button)
        self.toolbar.addWidget(recovery_button)

        if sys.platform != "win32":  # Text is getting clipped on Windows 10
            for action in self.toolbar.actions():
                widget = self.toolbar.widgetForAction(action)
                if isinstance(widget, QToolButton):
                    widget.setMaximumWidth(68)

        self.active_invite_sender_dialogs = []
        self.active_invite_receiver_dialogs = []

        self.pending_news_message = ()

    def populate(self, gateways):
        for gateway in gateways:
            if gateway not in self.gateways:
                self.central_widget.add_folders_view(gateway)
                self.central_widget.add_history_view(gateway)
                self.combo_box.add_gateway(gateway)
                self.gateways.append(gateway)
                gateway.newscap_checker.message_received.connect(
                    self.on_message_received
                )
                gateway.newscap_checker.upgrade_required.connect(
                    self.on_upgrade_required
                )

    def show_news_message(self, gateway, title, message):
        msgbox = QMessageBox(self)
        msgbox.setWindowModality(Qt.WindowModal)
        icon_filepath = os.path.join(gateway.nodedir, "icon")
        if os.path.exists(icon_filepath):
            msgbox.setIconPixmap(QIcon(icon_filepath).pixmap(64, 64))
        elif os.path.exists(resource("tahoe-lafs.png")):
            msgbox.setIconPixmap(
                QIcon(resource("tahoe-lafs.png")).pixmap(64, 64)
            )
        else:
            msgbox.setIcon(QMessageBox.Information)
        if sys.platform == "darwin":
            msgbox.setText(title)
            msgbox.setInformativeText(message)
        else:
            msgbox.setWindowTitle(title)
            msgbox.setText(message)
        msgbox.show()
        try:
            self.gui.unread_messages.remove((gateway, title, message))
        except ValueError:
            return
        self.gui.systray.update()

    def _maybe_show_news_message(self, gateway, title, message):
        self.gui.unread_messages.append((gateway, title, message))
        self.gui.systray.update()
        if self.isVisible():
            self.show_news_message(gateway, title, message)
        else:
            self.pending_news_message = (gateway, title, message)

    def on_message_received(self, gateway, message):
        title = "New message from {}".format(gateway.name)
        self.gui.show_message(
            title, strip_html_tags(message.replace("<p>", "\n\n"))
        )
        self._maybe_show_news_message(gateway, title, message)

    def on_upgrade_required(self, gateway):
        title = "Upgrade required"
        message = (
            "A message was received from {} in an unsupported format. This "
            "suggests that you are running an out-of-date version of {}.\n\n"
            "To avoid seeing this warning, please upgrade to the latest "
            "version.".format(gateway.name, APP_NAME)
        )
        self._maybe_show_news_message(gateway, title, message)

    def current_view(self):
        try:
            w = self.central_widget.folders_views[self.combo_box.currentData()]
        except KeyError:
            return None
        return w.layout().itemAt(0).widget()

    def select_folder(self):
        self.show_folders_view()
        view = self.current_view()
        if view:
            view.select_folder()

    def set_current_grid_status(self):
        current_view = self.current_view()
        if not current_view:
            return
        self.gui.systray.update()

    def show_folders_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.folders_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()

    def show_history_view(self):
        try:
            self.central_widget.setCurrentWidget(
                self.central_widget.history_views[self.combo_box.currentData()]
            )
        except KeyError:
            pass
        self.set_current_grid_status()

    def show_welcome_dialog(self):
        if self.welcome_dialog:
            self.welcome_dialog.close()
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()

    def on_grid_selected(self, index):
        if index == self.combo_box.count() - 1:
            self.show_welcome_dialog()
        if not self.combo_box.currentData():
            return
        if self.history_button.isChecked():
            self.show_history_view()
        else:
            self.show_folders_view()
        self.setWindowTitle(
            "{} - {}".format(APP_NAME, self.combo_box.currentData().name)
        )

    def confirm_export(self, path):
        if os.path.isfile(path):
            logging.info("Recovery Key successfully exported")
            info(
                self,
                "Export successful",
                "Recovery Key successfully exported to {}".format(path),
            )
        else:
            logging.error("Error exporting Recovery Key; file not found.")
            error(
                self,
                "Error exporting Recovery Key",
                "Destination file not found after export: {}".format(path),
            )

    def export_recovery_key(self, gateway=None):
        self.show_folders_view()
        if not gateway:
            gateway = self.combo_box.currentData()
        self.recovery_key_exporter = RecoveryKeyExporter(self)
        self.recovery_key_exporter.done.connect(self.confirm_export)
        self.recovery_key_exporter.do_export(gateway)

    def import_recovery_key(self):
        # XXX Quick hack for user-testing; change later
        self.welcome_dialog = WelcomeDialog(self.gui, self.gateways)
        self.welcome_dialog.on_restore_link_activated()

    def on_history_button_clicked(self):
        if not self.history_button.isChecked():
            self.history_button.setChecked(True)
            self.show_history_view()
        else:
            self.history_button.setChecked(False)
            self.show_folders_view()

    def on_invite_received(self, gateway):
        self.populate([gateway])
        for view in self.central_widget.views:
            view.model().monitor.scan_rootcap("star.png")

    def on_invite_closed(self, obj):
        try:
            self.active_invite_receiver_dialogs.remove(obj)
        except ValueError:
            pass

    def open_invite_receiver(self):
        invite_receiver_dialog = InviteReceiverDialog(self.gateways)
        invite_receiver_dialog.done.connect(self.on_invite_received)
        invite_receiver_dialog.closed.connect(self.on_invite_closed)
        invite_receiver_dialog.show()
        self.active_invite_receiver_dialogs.append(invite_receiver_dialog)

    def open_invite_sender_dialog(self):
        gateway = self.combo_box.currentData()
        if gateway:
            view = self.current_view()
            if view:
                invite_sender_dialog = InviteSenderDialog(
                    gateway, self.gui, view.get_selected_folders()
                )
            else:
                invite_sender_dialog = InviteSenderDialog(gateway, self.gui)
            invite_sender_dialog.closed.connect(
                self.active_invite_sender_dialogs.remove
            )
            invite_sender_dialog.show()
            self.active_invite_sender_dialogs.append(invite_sender_dialog)

    def confirm_quit(self):
        folder_loading = False
        folder_syncing = False
        for model in [view.model() for view in self.central_widget.views]:
            for row in range(model.rowCount()):
                status = model.item(row, 1).data(Qt.UserRole)
                mtime = model.item(row, 2).data(Qt.UserRole)
                if not status and not mtime:  # "Loading..." and not yet synced
                    folder_loading = True
                    break
                if status == 1:  # "Syncing"
                    folder_syncing = True
                    break
        msg = QMessageBox(self)
        if folder_loading:
            msg.setIcon(QMessageBox.Warning)
            informative_text = (
                "One or more folders have not finished loading. If these "
                "folders were recently added, you may need to add them again."
            )
        elif folder_syncing:
            msg.setIcon(QMessageBox.Warning)
            informative_text = (
                "One or more folders are currently syncing. If you quit, any "
                "pending upload or download operations will be cancelled "
                "until you launch {} again.".format(APP_NAME)
            )
        else:
            msg.setIcon(QMessageBox.Question)
            informative_text = (
                "If you quit, {} will stop synchronizing your folders until "
                "you launch it again.".format(APP_NAME)
            )
        if sys.platform == "darwin":
            msg.setText("Are you sure you wish to quit?")
            msg.setInformativeText(informative_text)
        else:
            msg.setWindowTitle("Exit {}?".format(APP_NAME))
            msg.setText(
                "Are you sure you wish to quit? {}".format(informative_text)
            )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        if msg.exec_() == QMessageBox.Yes:
            if sys.platform == "win32":
                self.gui.systray.hide()
            reactor.stop()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            view = self.current_view()
            selected = view.selectedIndexes() if view else None
            if selected:
                view.confirm_stop_syncing(view.get_selected_folders())
        if key == Qt.Key_Escape:
            view = self.current_view()
            selected = view.selectedIndexes() if view else None
            if selected:
                for index in selected:
                    view.selectionModel().select(
                        index, QItemSelectionModel.Deselect
                    )
            elif self.gui.systray.isSystemTrayAvailable():
                self.hide()

    def closeEvent(self, event):
        if self.gui.systray.isSystemTrayAvailable():
            event.accept()
        else:
            event.ignore()
            self.confirm_quit()

    def showEvent(self, _):
        if self.pending_news_message:
            gateway, title, message = self.pending_news_message
            self.pending_news_message = ()
            QTimer.singleShot(
                0, lambda: self.show_news_message(gateway, title, message)
            )
