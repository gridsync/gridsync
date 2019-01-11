# -*- coding: utf-8 -*-

import logging as log
import sys

from PyQt5.QtCore import QCoreApplication, Qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QGridLayout, QLabel, QPushButton, QMessageBox, QProgressBar, QShortcut,
    QSizePolicy, QSpacerItem, QStackedWidget, QToolButton, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError
from wormhole.errors import (
    ServerConnectionError, WelcomeError, WrongPasswordError)

from gridsync import resource, APP_NAME
from gridsync import settings as global_settings
from gridsync.invite import InviteReceiver
from gridsync.errors import UpgradeRequiredError
from gridsync.gui.invite import InviteCodeWidget, show_failure
from gridsync.gui.widgets import TahoeConfigForm
from gridsync.recovery import RecoveryKeyImporter
from gridsync.setup import SetupRunner, validate_settings
from gridsync.tahoe import is_valid_furl
from gridsync.tor import TOR_PURPLE


class WelcomeWidget(QWidget):
    def __init__(self, parent=None):
        super(WelcomeWidget, self).__init__()
        self.parent = parent

        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(resource(
            global_settings['application']['tray_icon'])).scaled(
                220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.icon.setAlignment(Qt.AlignCenter)

        self.slogan = QLabel("<i>{}</i>".format(
            global_settings['application']['description']))
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(16)
        else:
            font.setPointSize(12)
        self.slogan.setFont(font)
        self.slogan.setStyleSheet("color: grey")
        self.slogan.setAlignment(Qt.AlignCenter)

        self.invite_code_widget = InviteCodeWidget(self)
        self.lineedit = self.invite_code_widget.lineedit

        self.message = QLabel()
        self.message.setStyleSheet("color: red")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.hide()

        self.restore_link = QLabel()
        self.restore_link.setText("<a href>Restore from Recovery Key...</a>")
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(12)
        else:
            font.setPointSize(9)
        self.restore_link.setFont(font)
        self.restore_link.setAlignment(Qt.AlignCenter)

        self.configure_link = QLabel()
        self.configure_link.setText("<a href>Manual configuration...</a>")
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(12)
        else:
            font.setPointSize(9)
        self.configure_link.setFont(font)
        self.configure_link.setAlignment(Qt.AlignCenter)

        self.preferences_button = QPushButton()
        self.preferences_button.setIcon(QIcon(resource('preferences.png')))
        self.preferences_button.setStyleSheet('border: 0px; padding: 0px;')
        self.preferences_button.setToolTip("Preferences...")
        self.preferences_button.setFocusPolicy(Qt.NoFocus)

        links_grid = QGridLayout()
        links_grid.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 1, 1)
        links_grid.addWidget(self.restore_link, 2, 1)
        links_grid.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 3, 1)
        links_grid.addWidget(self.configure_link, 4, 1)
        links_grid.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 5, 1)

        prefs_layout = QGridLayout()
        prefs_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        prefs_layout.addWidget(self.preferences_button, 1, 2)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addWidget(self.icon, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addWidget(self.slogan, 2, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 3, 1)
        layout.addWidget(self.invite_code_widget, 4, 2, 1, 3)
        layout.addWidget(self.message, 5, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Minimum), 6, 1)
        layout.addLayout(links_grid, 7, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Minimum), 8, 1)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 9, 1)
        layout.addLayout(prefs_layout, 10, 1, 1, 5)

    def show_error(self, message):
        self.message.setText(message)
        self.message.show()
        reactor.callLater(3, self.message.hide)

    def reset(self):
        self.lineedit.setText('')


class ProgressBarWidget(QWidget):
    def __init__(self):
        super(ProgressBarWidget, self).__init__()

        self.icon_server = QLabel()
        self.icon_server.setPixmap(
            QPixmap(resource('cloud.png')).scaled(220, 220))
        self.icon_server.setAlignment(Qt.AlignCenter)

        self.icon_overlay = QLabel()
        self.icon_overlay.setPixmap(
            QPixmap(resource('pixel.png')).scaled(75, 75))
        self.icon_overlay.setAlignment(Qt.AlignHCenter)

        self.icon_connection = QLabel()
        self.icon_connection.setPixmap(
            QPixmap(resource('wifi.png')).scaled(128, 128))
        self.icon_connection.setAlignment(Qt.AlignCenter)

        self.icon_client = QLabel()
        self.icon_client.setPixmap(
            QPixmap(resource('laptop-with-icon.png')).scaled(128, 128))
        self.icon_client.setAlignment(Qt.AlignCenter)

        self.checkmark = QLabel()
        self.checkmark.setPixmap(
            QPixmap(resource('pixel.png')).scaled(32, 32))
        self.checkmark.setAlignment(Qt.AlignCenter)

        self.tor_label = QLabel()
        self.tor_label.setToolTip(
            "This connection is being routed through the Tor network.")
        self.tor_label.setPixmap(
            QPixmap(resource('tor-onion.png')).scaled(
                24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.tor_label.hide()

        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(10)
        self.progressbar.setTextVisible(False)
        self.progressbar.setValue(0)

        self.message = QLabel()
        self.message.setStyleSheet("color: grey")
        self.message.setAlignment(Qt.AlignCenter)

        self.finish_button = QPushButton("Finish")
        self.finish_button.hide()

        self.cancel_button = QToolButton()
        self.cancel_button.setIcon(QIcon(resource('close.png')))
        self.cancel_button.setStyleSheet('border: 0px; padding: 0px;')

        layout = QGridLayout(self)
        layout.addWidget(self.cancel_button, 0, 5)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addWidget(self.icon_server, 1, 3)
        layout.addWidget(self.icon_overlay, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addWidget(self.icon_connection, 2, 3)
        layout.addWidget(self.icon_client, 3, 3)
        layout.addWidget(self.checkmark, 4, 3, 1, 1)
        layout.addWidget(self.tor_label, 5, 1, 1, 1, Qt.AlignRight)
        layout.addWidget(self.progressbar, 5, 2, 1, 3)
        layout.addWidget(self.message, 6, 3)
        layout.addWidget(self.finish_button, 6, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 7, 1)

    def update_progress(self, message):
        step = self.progressbar.value() + 1
        self.progressbar.setValue(step)
        self.message.setText(message)
        if step == 2:  # "Connecting to <nickname>..."
            self.icon_connection.setPixmap(
                QPixmap(resource('lines_dotted.png')).scaled(128, 128))
            self.icon_server.setPixmap(
                QPixmap(resource('cloud_storage.png')).scaled(220, 220))
        elif step == 5:  # After await_ready()
            self.icon_connection.setPixmap(
                QPixmap(resource('lines_solid.png')).scaled(128, 128))
        elif step == self.progressbar.maximum():  # "Done!"
            self.checkmark.setPixmap(
                QPixmap(resource('green_checkmark.png')).scaled(32, 32))

    def is_complete(self):
        return self.progressbar.value() == self.progressbar.maximum()

    def reset(self):
        self.progressbar.setValue(0)
        self.message.setText('')
        self.finish_button.hide()
        self.checkmark.setPixmap(
            QPixmap(resource('pixel.png')).scaled(32, 32))
        self.tor_label.hide()
        self.progressbar.setStyleSheet('')


class WelcomeDialog(QStackedWidget):
    def __init__(self, gui, known_gateways=None):
        super(WelcomeDialog, self).__init__()
        self.gui = gui
        self.known_gateways = known_gateways
        self.gateway = None
        self.setup_runner = None
        self.recovery_key_importer = None
        self.use_tor = False
        self.prompt_to_export = True
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
        self.restore_link.linkActivated.connect(
            self.on_restore_link_activated)
        self.configure_link.linkActivated.connect(
            self.on_configure_link_activated)
        self.preferences_button.clicked.connect(
            self.gui.show_preferences_window)

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
        self.page_2.icon_overlay.setPixmap(
            QPixmap(filepath).scaled(100, 100))

    def handle_failure(self, failure):
        log.error(str(failure))
        if failure.type == CancelledError:
            if self.progressbar.value() <= 2:
                show_failure(failure, self)
                self.show_error("Invite timed out")
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
        self.page_2.checkmark.setPixmap(
            QPixmap(resource('green_checkmark.png')).scaled(32, 32))
        self.finish_button.show()
        self.finish_button_clicked()  # TODO: Cleanup

    def on_already_joined(self, grid_name):
        QMessageBox.information(
            self,
            "Already connected",
            'You are already connected to "{}"'.format(grid_name)
        )
        self.close()

    def verify_settings(self, settings, from_wormhole=True):
        self.show()
        self.raise_()
        settings = validate_settings(
            settings, self.known_gateways, self, from_wormhole)
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
        if settings.get('hide-ip') or self.tor_checkbox.isChecked():
            self.use_tor = True
            self.page_2.tor_label.show()
            self.progressbar.setStyleSheet(
                'QProgressBar::chunk {{ background-color: {}; }}'.format(
                    TOR_PURPLE))
        self.setCurrentIndex(1)
        self.progressbar.setValue(1)
        self.update_progress('Verifying invitation code...')
        self.prompt_to_export = False
        self.verify_settings(settings, from_wormhole=False)

    def on_restore_link_activated(self):
        self.recovery_key_importer = RecoveryKeyImporter(self.page_1)
        self.recovery_key_importer.done.connect(self.on_import_done)
        self.recovery_key_importer.do_import()

    def go(self, code):
        if self.tor_checkbox.isChecked():
            self.use_tor = True
            self.page_2.tor_label.show()
            self.progressbar.setStyleSheet(
                'QProgressBar::chunk {{ background-color: {}; }}'.format(
                    TOR_PURPLE))
        self.setCurrentIndex(1)
        self.progressbar.setValue(1)
        self.update_progress('Verifying invitation code...')
        invite_receiver = InviteReceiver(self.known_gateways, self.use_tor)
        invite_receiver.grid_already_joined.connect(self.on_already_joined)
        invite_receiver.update_progress.connect(self.update_progress)
        invite_receiver.got_icon.connect(self.load_service_icon)
        invite_receiver.client_started.connect(
            lambda gateway: self.gui.populate([gateway])
        )
        invite_receiver.done.connect(self.on_done)
        d = invite_receiver.receive(code)
        d.addErrback(self.handle_failure)
        reactor.callLater(30, d.cancel)

    def cancel_button_clicked(self):
        if self.page_2.is_complete():
            self.finish_button_clicked()
            return
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Question)
        msgbox.setWindowTitle("Cancel setup?")
        msgbox.setText("Are you sure you wish to cancel the setup process?")
        msgbox.setInformativeText(
            "If you cancel, you may need to obtain a new invite code.")
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
        if not settings['nickname']:
            msg.setText("Please enter a name.")
            msg.exec_()
        elif not settings['introducer']:
            msg.setText("Please enter an Introducer fURL.")
            msg.exec_()
        elif not is_valid_furl(settings['introducer']):
            msg.setText("Please enter a valid Introducer fURL.")
            msg.exec_()
        else:
            self.setCurrentIndex(1)
            self.verify_settings(settings, from_wormhole=False)

    def prompt_for_export(self, gateway):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        button_export = msg.button(QMessageBox.Yes)
        button_export.setText("&Export...")
        button_skip = msg.button(QMessageBox.No)
        button_skip.setText("&Skip")
        msg.setWindowTitle("Export Recovery Key?")
        # "Now that {} is configured..."
        msg.setText(
            "Before uploading any folders to {}, it is recommended that you "
            "export a Recovery Key and store it in a safe location (such as "
            "an encrypted USB drive or password manager).".format(gateway.name)
        )
        msg.setInformativeText(
            "{} does not have access to your folders, and cannot restore "
            "access to them. But with a Recovery Key, you can restore access "
            "to uploaded folders in case something goes wrong (e.g., hardware "
            "failure, accidental data-loss).<p><p><a href=https://github.com/"
            "gridsync/gridsync/blob/master/docs/recovery-keys.md>More "
            "information...</a>".format(gateway.name)
        )
        #msg.setText(
        #    "Before uploading any folders to {}, it is <b>strongly "
        #    "recommended</b> that you <i>export a Recovery Key</i> and store "
        #    "it in a safe and secure location (such as an encrypted USB drive)"
        #    ".<p><p>Possessing a Recovery Key will allow you to restore "
        #    "access to any of the folders you've uploaded to {} in the event "
        #    "that something goes wrong (e.g., hardware failure, accidental "
        #    "data-loss).".format(gateway.name, gateway.name))
        #msg.setDetailedText(
        #    "A 'Recovery Key' is a small file that contains enough information"
        #    " to re-establish a connection with your storage provider and "
        #    "restore your previously-uploaded folders. Because access to this "
        #    "file is sufficient to access to any of the the data you've "
        #    "stored, it is important that you keep this file safe and secure; "
        #    "do not share your Recovery Key with anybody!")
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            self.gui.main_window.export_recovery_key()  # XXX
        else:
            # TODO: Nag user; "Are you sure?"
            pass

    def finish_button_clicked(self):
        self.gui.show()
        self.close()
        if self.prompt_to_export:
            self.prompt_for_export(self.gateway)
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
                "{} has not yet been configured.".format(APP_NAME))
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            if msgbox.exec_() == QMessageBox.Yes:
                QCoreApplication.instance().quit()
