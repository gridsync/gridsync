# -*- coding: utf-8 -*-

import logging as log
import sys

from qtpy.QtCore import QCoreApplication, Qt
from qtpy.QtGui import QIcon, QKeySequence
from qtpy.QtWidgets import (
    QGridLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QShortcut,
    QStackedWidget,
    QToolButton,
    QWidget,
)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError
from wormhole.errors import (
    ServerConnectionError,
    WelcomeError,
    WrongPasswordError,
)

from gridsync import APP_NAME, load_settings_from_cheatcode, resource
from gridsync import settings as global_settings
from gridsync.errors import AbortedByUserError, UpgradeRequiredError
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.invite import InviteCodeWidget, show_failure
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.widgets import HSpacer, TahoeConfigForm, VSpacer
from gridsync.invite import InviteReceiver
from gridsync.recovery import RecoveryKeyImporter
from gridsync.setup import SetupRunner, validate_settings
from gridsync.tahoe import is_valid_furl
from gridsync.tor import TOR_PURPLE


class WelcomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent

        application_settings = global_settings["application"]
        logo_icon = application_settings.get("logo_icon")
        if logo_icon:
            icon_file = logo_icon
            icon_size = 288
        else:
            icon_file = application_settings.get("tray_icon")
            icon_size = 220

        self.icon = QLabel()
        self.icon.setPixmap(Pixmap(icon_file, icon_size))
        self.icon.setAlignment(Qt.AlignCenter)

        self.slogan = QLabel(
            "<i>{}</i>".format(application_settings.get("description", ""))
        )
        self.slogan.setFont(Font(12))
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color()
        ).name()
        self.slogan.setStyleSheet("color: {}".format(dimmer_grey))
        self.slogan.setAlignment(Qt.AlignCenter)
        if logo_icon:
            self.slogan.hide()

        self.invite_code_widget = InviteCodeWidget(self)
        self.lineedit = self.invite_code_widget.lineedit

        self.connect_button = QPushButton("Connect")

        try:
            default_code = global_settings["connection"]["default"]
        except KeyError:
            default_code = ""
        grid_settings = load_settings_from_cheatcode(default_code)
        if grid_settings:
            self.invite_code_widget.hide()
            nickname = grid_settings.get("nickname")
            if nickname:
                font = Font(11)
                self.connect_button.setFont(font)
                self.connect_button.setFixedHeight(32)
                self.connect_button.setText(f"Connect to {nickname}")
                self.connect_button.clicked.connect(
                    lambda: self.parent.go(default_code, grid_settings)
                )
            primary_color = grid_settings.get("color-1")
            if primary_color:
                self.connect_button.setStyleSheet(
                    f"background: {primary_color}; color: white"
                )
            else:
                self.connect_button.setStyleSheet(
                    "background: green; color: white"
                )
        else:
            self.connect_button.hide()

        self.message = QLabel()
        self.message.setStyleSheet("color: red")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.hide()

        self.restore_link = QLabel()
        self.restore_link.setText("<a href>Restore from Recovery Key...</a>")
        self.restore_link.setFont(Font(9))
        self.restore_link.setAlignment(Qt.AlignCenter)

        self.configure_link = QLabel()
        self.configure_link.setText("<a href>Manual configuration...</a>")
        self.configure_link.setFont(Font(9))
        self.configure_link.setAlignment(Qt.AlignCenter)

        self.preferences_button = QPushButton()
        self.preferences_button.setIcon(QIcon(resource("preferences.png")))
        self.preferences_button.setStyleSheet("border: 0px; padding: 0px;")
        self.preferences_button.setToolTip("Preferences...")
        self.preferences_button.setFocusPolicy(Qt.NoFocus)

        links_grid = QGridLayout()
        links_grid.addItem(VSpacer(), 1, 1)
        links_grid.addWidget(self.restore_link, 2, 1)
        links_grid.addItem(VSpacer(), 3, 1)
        links_grid.addWidget(self.configure_link, 4, 1)
        links_grid.addItem(VSpacer(), 5, 1)

        prefs_layout = QGridLayout()
        prefs_layout.addItem(HSpacer(), 1, 1)
        prefs_layout.addWidget(self.preferences_button, 1, 2)

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 0, 0)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addWidget(self.icon, 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.slogan, 2, 3)
        layout.addItem(VSpacer(), 3, 1)
        layout.addWidget(self.invite_code_widget, 4, 2, 1, 3)
        layout.addWidget(self.connect_button, 4, 2, 1, 3)
        layout.addWidget(self.message, 5, 3)
        layout.addItem(HSpacer(), 6, 1)
        layout.addLayout(links_grid, 7, 3)
        layout.addItem(HSpacer(), 8, 1)
        layout.addItem(VSpacer(), 9, 1)
        layout.addLayout(prefs_layout, 10, 1, 1, 5)

    def show_error(self, message):
        self.message.setText(message)
        self.message.show()
        reactor.callLater(3, self.message.hide)

    def reset(self):
        self.lineedit.setText("")


class ProgressBarWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.icon_server = QLabel()
        self.icon_server.setPixmap(Pixmap("cloud.png", 220))
        self.icon_server.setAlignment(Qt.AlignCenter)

        self.icon_overlay = QLabel()
        self.icon_overlay.setPixmap(Pixmap("pixel.png", 75))
        self.icon_overlay.setAlignment(Qt.AlignHCenter)

        self.icon_connection = QLabel()
        self.icon_connection.setPixmap(Pixmap("wifi.png", 128))
        self.icon_connection.setAlignment(Qt.AlignCenter)

        self.icon_client = QLabel()
        self.icon_client.setPixmap(Pixmap("laptop-with-icon.png", 128))
        self.icon_client.setAlignment(Qt.AlignCenter)

        self.checkmark = QLabel()
        self.checkmark.setPixmap(Pixmap("pixel.png", 32))
        self.checkmark.setAlignment(Qt.AlignCenter)

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network."
        )
        self.tor_label.setPixmap(Pixmap("tor-onion.png", 24))
        self.tor_label.hide()

        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(10)
        self.progressbar.setTextVisible(False)
        self.progressbar.setValue(0)

        self.message = QLabel()
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color()
        ).name()
        self.message.setStyleSheet("color: {}".format(dimmer_grey))
        self.message.setAlignment(Qt.AlignCenter)

        self.finish_button = QPushButton("Finish")
        self.finish_button.hide()

        self.cancel_button = QToolButton()
        self.cancel_button.setIcon(QIcon(resource("close.png")))
        self.cancel_button.setStyleSheet("border: 0px; padding: 0px;")

        layout = QGridLayout(self)
        layout.addWidget(self.cancel_button, 0, 5)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addWidget(self.icon_server, 1, 3)
        layout.addWidget(self.icon_overlay, 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.icon_connection, 2, 3)
        layout.addWidget(self.icon_client, 3, 3)
        layout.addWidget(self.checkmark, 4, 3, 1, 1)
        layout.addWidget(self.tor_label, 5, 1, 1, 1, Qt.AlignRight)
        layout.addWidget(self.progressbar, 5, 2, 1, 3)
        layout.addWidget(self.message, 6, 3)
        layout.addWidget(self.finish_button, 6, 3)
        layout.addItem(VSpacer(), 7, 1)

    def update_progress(self, message):
        step = self.progressbar.value() + 1
        self.progressbar.setValue(step)
        self.message.setText(message)
        if step == 2:  # "Connecting to <nickname>..."
            self.icon_connection.setPixmap(Pixmap("lines_dotted.png", 128))
            self.icon_server.setPixmap(Pixmap("cloud_storage.png", 220))
        elif step == 5:  # After await_ready()
            self.icon_connection.setPixmap(Pixmap("lines_solid.png", 128))
        elif step == self.progressbar.maximum():  # "Done!"
            self.checkmark.setPixmap(Pixmap("green_checkmark.png", 32))

    def is_complete(self):
        return self.progressbar.value() == self.progressbar.maximum()

    def reset(self):
        self.progressbar.setValue(0)
        self.message.setText("")
        self.finish_button.hide()
        self.checkmark.setPixmap(Pixmap("pixel.png", 32))
        self.tor_label.hide()
        self.progressbar.setStyleSheet("")


class WelcomeDialog(QStackedWidget):
    def __init__(self, gui, known_gateways=None):
        super().__init__()
        self.gui = gui
        self.known_gateways = known_gateways
        self.gateway = None
        self.setup_runner = None
        self.recovery_key_importer = None
        self.use_tor = False
        self.resize(400, 500)
        self.setWindowTitle(APP_NAME)
        self.page_1 = WelcomeWidget(self)
        self.page_2 = ProgressBarWidget()
        self.page_3 = TahoeConfigForm()

        self.addWidget(self.page_1)
        self.addWidget(self.page_2)
        self.addWidget(self.page_3)

        self.lineedit = self.page_1.lineedit
        self.tor_checkbox = self.page_1.invite_code_widget.tor_checkbox
        self.restore_link = self.page_1.restore_link
        self.configure_link = self.page_1.configure_link
        self.preferences_button = self.page_1.preferences_button

        self.progressbar = self.page_2.progressbar
        self.cancel_button = self.page_2.cancel_button
        self.finish_button = self.page_2.finish_button

        self.buttonbox = self.page_3.buttonbox

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.close)

        self.lineedit.go.connect(self.go)
        self.lineedit.error.connect(self.show_error)
        self.restore_link.linkActivated.connect(self.on_restore_link_activated)
        self.configure_link.linkActivated.connect(
            self.on_configure_link_activated
        )
        self.preferences_button.clicked.connect(
            self.gui.show_preferences_window
        )

        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.finish_button.clicked.connect(self.finish_button_clicked)

        self.buttonbox.accepted.connect(self.on_accepted)
        self.buttonbox.rejected.connect(self.reset)

    def on_configure_link_activated(self):
        self.setCurrentIndex(2)

    def update_progress(self, message):
        self.page_2.update_progress(message)

    def show_error(self, message):
        self.page_1.show_error(message)

    def reset(self):
        self.page_1.reset()
        self.page_2.reset()
        self.page_3.reset()
        self.setCurrentIndex(0)

    def load_service_icon(self, filepath):
        self.page_2.icon_overlay.setPixmap(Pixmap(filepath, 100))

    def handle_failure(self, failure):
        log.error(str(failure))
        if failure.type == CancelledError:
            if self.progressbar.value() <= 2:
                show_failure(failure, self)
                self.show_error("Invite timed out")
                self.reset()
            return
        if failure.type == AbortedByUserError:
            self.show_error("Operation aborted")
            self.reset()
            return
        show_failure(failure, self)
        if failure.type == ServerConnectionError:
            self.show_error("Server connection error")
        if failure.type == WelcomeError:
            self.show_error("Invite refused")
        elif failure.type == WrongPasswordError:
            self.show_error("Invite confirmation failed")
        elif failure.type == UpgradeRequiredError:
            self.show_error("Upgrade required")
        else:
            self.show_error(str(failure.type.__name__))
        self.reset()

    def on_done(self, gateway):
        self.gateway = gateway
        self.progressbar.setValue(self.progressbar.maximum())
        self.page_2.checkmark.setPixmap(Pixmap("green_checkmark.png", 32))
        self.finish_button.show()
        self.finish_button_clicked()  # TODO: Cleanup

    def on_already_joined(self, grid_name):
        QMessageBox.information(
            self,
            "Already connected",
            'You are already connected to "{}"'.format(grid_name),
        )
        self.close()

    def verify_settings(self, settings, from_wormhole=True):
        self.show()
        self.raise_()
        settings = validate_settings(
            settings, self.known_gateways, self, from_wormhole
        )
        self.setup_runner = SetupRunner(self.known_gateways, self.use_tor)
        steps = self.setup_runner.calculate_total_steps(settings) + 2
        self.progressbar.setMaximum(steps)
        self.setup_runner.grid_already_joined.connect(self.on_already_joined)
        self.setup_runner.update_progress.connect(self.update_progress)
        self.setup_runner.got_icon.connect(self.load_service_icon)
        self.setup_runner.client_started.connect(
            lambda gateway: self.gui.populate([gateway])
        )
        self.setup_runner.done.connect(self.on_done)
        d = self.setup_runner.run(settings)
        d.addErrback(self.handle_failure)

    def on_import_done(self, settings):
        if settings.get("hide-ip") or self.tor_checkbox.isChecked():
            self.use_tor = True
            self.page_2.tor_label.show()
            self.progressbar.setStyleSheet(
                "QProgressBar::chunk {{ background-color: {}; }}".format(
                    TOR_PURPLE
                )
            )
        self.setCurrentIndex(1)
        self.progressbar.setValue(1)
        self.update_progress("Verifying invitation code...")
        self.verify_settings(settings, from_wormhole=False)

    def on_restore_link_activated(self):
        self.recovery_key_importer = RecoveryKeyImporter(self.page_1)
        self.recovery_key_importer.done.connect(self.on_import_done)
        self.recovery_key_importer.do_import()

    def go(self, code, settings=None):
        if self.tor_checkbox.isChecked():
            self.use_tor = True
            self.page_2.tor_label.show()
            self.progressbar.setStyleSheet(
                "QProgressBar::chunk {{ background-color: {}; }}".format(
                    TOR_PURPLE
                )
            )
        self.setCurrentIndex(1)
        self.progressbar.setValue(1)
        self.update_progress("Verifying invitation code...")
        invite_receiver = InviteReceiver(self.known_gateways, self.use_tor)
        invite_receiver.grid_already_joined.connect(self.on_already_joined)
        invite_receiver.update_progress.connect(self.update_progress)
        invite_receiver.got_icon.connect(self.load_service_icon)
        invite_receiver.client_started.connect(
            lambda gateway: self.gui.populate([gateway])
        )
        invite_receiver.done.connect(self.on_done)
        d = invite_receiver.receive(code, settings)
        d.addErrback(self.handle_failure)
        # reactor.callLater(30, d.cancel)  # XXX

    def cancel_button_clicked(self):
        if self.page_2.is_complete():
            self.finish_button_clicked()
            return
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setWindowTitle("Cancel setup?")
        msgbox.setText("Are you sure you wish to cancel the setup process?")
        msgbox.setInformativeText(
            "If you cancel, you may need to obtain a new invite code."
        )
        msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgbox.setDefaultButton(QMessageBox.No)
        if msgbox.exec_() == QMessageBox.Yes:
            self.reset()

    def on_accepted(self):
        settings = self.page_3.get_settings()
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(APP_NAME)
        msg.setStandardButtons(QMessageBox.Ok)
        if not settings["nickname"]:
            msg.setText("Please enter a name.")
            msg.exec_()
        elif not settings["introducer"]:
            msg.setText("Please enter an Introducer fURL.")
            msg.exec_()
        elif not is_valid_furl(settings["introducer"]):
            msg.setText("Please enter a valid Introducer fURL.")
            msg.exec_()
        else:
            self.setCurrentIndex(1)
            self.verify_settings(settings, from_wormhole=False)

    def finish_button_clicked(self):
        self.gui.show_main_window()
        self.close()
        if self.gateway.zkapauthorizer.zkap_payment_url_root:  # XXX
            self.gui.main_window.show_usage_view()
        self.reset()

    def enterEvent(self, event):
        event.accept()
        self.page_1.invite_code_widget.maybe_enable_tor_checkbox()
        self.lineedit.update_action_button()

    def closeEvent(self, event):
        if self.gui.main_window.gateways:
            event.accept()
        else:
            event.ignore()
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Question)
            msgbox.setWindowTitle("Exit setup?")
            msgbox.setText("Are you sure you wish to exit?")
            msgbox.setInformativeText(
                "{} has not yet been configured.".format(APP_NAME)
            )
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            if msgbox.exec_() == QMessageBox.Yes:
                if sys.platform == "win32":
                    self.gui.systray.hide()
                QCoreApplication.instance().quit()
