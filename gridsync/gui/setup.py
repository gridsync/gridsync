# -*- coding: utf-8 -*-

import base64
import json
import logging as log
import os
import shutil
from binascii import Error

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QInputDialog, QGridLayout, QLabel,
    QPushButton, QMessageBox, QProgressBar, QShortcut, QSizePolicy,
    QSpacerItem, QStackedWidget, QToolButton, QWidget)
import treq
from twisted.internet import reactor
from twisted.internet.defer import CancelledError, inlineCallbacks
from wormhole.errors import (
    ServerConnectionError, WelcomeError, WrongPasswordError)

from gridsync import config_dir, resource, APP_NAME
from gridsync.errors import UpgradeRequiredError
from gridsync.invite import wormhole_receive, InviteCodeLineEdit
from gridsync.tahoe import is_valid_furl, Tahoe
from gridsync.gui.widgets import TahoeConfigForm


class CodeEntryWidget(QWidget):
    def __init__(self, parent=None):
        super(CodeEntryWidget, self).__init__()
        self.parent = parent

        self.icon = QLabel()
        pixmap = QPixmap(resource('gridsync.png')).scaled(220, 220)
        self.icon.setPixmap(pixmap)
        self.icon.setAlignment(Qt.AlignCenter)

        self.slogan = QLabel("<i>Secure, distributed storage</i>")
        font = QFont()
        font.setPointSize(12)
        self.slogan.setFont(font)
        self.slogan.setStyleSheet("color: grey")
        self.slogan.setAlignment(Qt.AlignCenter)

        self.label = QLabel("Enter invite code:")
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: grey")
        self.label.setAlignment(Qt.AlignCenter)

        self.lineedit = InviteCodeLineEdit(self)

        self.checkbox = QCheckBox("Connect over the Tor network")
        self.checkbox.setEnabled(True)
        self.checkbox.setCheckable(False)
        self.checkbox.setStyleSheet("color: grey")
        self.checkbox.setFocusPolicy(Qt.NoFocus)

        self.message = QLabel()
        self.message.setStyleSheet("color: red")
        self.message.setAlignment(Qt.AlignCenter)
        self.message.hide()

        self.help = QLabel()
        self.help.setText("<a href>I don't have an invite code</a>")
        font = QFont()
        font.setPointSize(9)
        self.help.setFont(font)
        self.help.setAlignment(Qt.AlignCenter)
        #self.help.linkActivated.connect(self.on_click)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        layout.addWidget(self.icon, 1, 3)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)
        layout.addWidget(self.slogan, 2, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 3, 1)
        layout.addWidget(self.label, 4, 3, 1, 1)
        layout.addWidget(self.lineedit, 5, 2, 1, 3)
        #layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 6, 1)
        #layout.addWidget(self.checkbox, 6, 3, 1, 1, Qt.AlignCenter)
        layout.addWidget(self.message, 7, 3)
        layout.addWidget(self.help, 8, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 9, 1)

    def show_error(self, message):
        self.message.setText(message)
        #self.checkbox.hide()
        self.message.show()
        reactor.callLater(3, self.message.hide)
        #reactor.callLater(3, self.checkbox.show)

    def reset(self):
        self.lineedit.setText('')


class ProgressBarWidget(QWidget):
    def __init__(self):
        super(ProgressBarWidget, self).__init__()
        self.step = 0

        self.icon_server = QLabel()
        pixmap = QPixmap(resource('cloud.png')).scaled(220, 220)
        self.icon_server.setPixmap(pixmap)
        self.icon_server.setAlignment(Qt.AlignCenter)

        self.icon_overlay = QLabel()
        pixmap = QPixmap(resource('pixel.png')).scaled(75, 75)
        self.icon_overlay.setPixmap(pixmap)
        self.icon_overlay.setAlignment(Qt.AlignHCenter)

        self.icon_connection = QLabel()
        pixmap = QPixmap(resource('wifi.png')).scaled(128, 128)
        self.icon_connection.setPixmap(pixmap)
        self.icon_connection.setAlignment(Qt.AlignCenter)

        self.icon_client = QLabel()
        pixmap = QPixmap(resource('laptop-with-icon.png')).scaled(128, 128)
        self.icon_client.setPixmap(pixmap)
        self.icon_client.setAlignment(Qt.AlignCenter)

        self.checkmark = QLabel()
        pixmap = QPixmap(resource('pixel.png')).scaled(32, 32)
        self.checkmark.setPixmap(pixmap)
        self.checkmark.setAlignment(Qt.AlignCenter)

        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(6)
        self.progressbar.setTextVisible(False)

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
        layout.addWidget(self.progressbar, 5, 2, 1, 3)
        layout.addWidget(self.message, 6, 3)
        layout.addWidget(self.finish_button, 6, 3)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 7, 1)

    def update_progress(self, step, message):
        self.step = step
        self.progressbar.setValue(step)
        self.message.setText(message)
        if step == 2:  # "Connecting to <nickname>..."
            pixmap = QPixmap(resource('lines_dotted.png')).scaled(128, 128)
            self.icon_connection.setPixmap(pixmap)
            pixmap = QPixmap(resource('cloud_storage.png')).scaled(220, 220)
            self.icon_server.setPixmap(pixmap)
        elif step == 5:  # "Done!"
            pixmap = QPixmap(resource('lines_solid.png')).scaled(128, 128)
            self.icon_connection.setPixmap(pixmap)
            pixmap = QPixmap(resource('green_checkmark.png')).scaled(32, 32)
            self.checkmark.setPixmap(pixmap)

    def is_complete(self):
        if self.progressbar.value() == self.progressbar.maximum():
            return True

    def reset(self):
        self.update_progress(0, '')
        self.finish_button.hide()
        pixmap = QPixmap(resource('pixel.png')).scaled(32, 32)
        self.checkmark.setPixmap(pixmap)


class SetupForm(QStackedWidget):
    def __init__(self, gui):
        super(SetupForm, self).__init__()
        self.gui = gui
        self.gateway = None
        self.resize(400, 500)
        self.setWindowTitle(APP_NAME)
        self.page_1 = CodeEntryWidget(self)
        self.page_2 = ProgressBarWidget()
        self.page_3 = TahoeConfigForm()

        self.addWidget(self.page_1)
        self.addWidget(self.page_2)
        self.addWidget(self.page_3)

        self.lineedit = self.page_1.lineedit
        self.cancel_button = self.page_2.cancel_button
        self.finish_button = self.page_2.finish_button
        self.buttonbox = self.page_3.buttonbox
        self.help = self.page_1.help

        self.shortcut_close = QShortcut(QKeySequence.Close, self)
        self.shortcut_close.activated.connect(self.close)

        self.shortcut_quit = QShortcut(QKeySequence.Quit, self)
        self.shortcut_quit.activated.connect(self.close)

        self.lineedit.go.connect(self.go)
        self.lineedit.error.connect(self.show_error)
        self.cancel_button.clicked.connect(self.cancel_button_clicked)
        self.finish_button.clicked.connect(self.finish_button_clicked)
        self.buttonbox.accepted.connect(self.on_accepted)
        self.buttonbox.rejected.connect(self.reset)
        self.help.linkActivated.connect(self.on_link_activated)

    def on_link_activated(self):
        self.setCurrentIndex(2)

    def update_progress(self, step, message):
        self.page_2.update_progress(step, message)

    def show_error(self, message):
        self.page_1.show_error(message)

    def reset(self):
        self.page_1.reset()
        self.page_2.reset()
        self.page_3.reset()
        self.setCurrentIndex(0)

    def load_service_icon(self, filepath):
        pixmap = QPixmap(filepath).scaled(100, 100)
        self.page_2.icon_overlay.setPixmap(pixmap)

    @inlineCallbacks  # noqa: max-complexity=15 XXX
    def setup(self, settings):  # pylint: disable=too-many-statements,too-many-branches
        if 'version' in settings and int(settings['version']) > 1:
            raise UpgradeRequiredError

        if 'nickname' in settings:
            nickname = settings['nickname']
        else:
            nickname = settings['introducer'].split('@')[1].split(':')[0]

        self.update_progress(2, 'Connecting to {}...'.format(nickname))
        icon_path = None
        if nickname == 'Least Authority S4':
            icon_path = resource('leastauthority.com.icon')
            self.load_service_icon(icon_path)
        elif 'icon_base64' in settings:
            icon_path = os.path.join(config_dir, '.icon.tmp')
            with open(icon_path, 'wb') as f:
                try:
                    f.write(base64.b64decode(settings['icon_base64']))
                except (Error, TypeError):
                    pass
            self.load_service_icon(icon_path)
        elif 'icon_url' in settings:
            # A temporary(?) measure to get around the performance issues
            # observed when transferring a base64-encoded icon through Least
            # Authority's wormhole server. Hopefully this will go away.. See:
            # https://github.com/LeastAuthority/leastauthority.com/issues/539
            log.debug("Fetching service icon from %s...", settings['icon_url'])
            icon_path = os.path.join(config_dir, '.icon.tmp')
            try:
                # It's probably not worth cancelling or holding-up the setup
                # process if fetching/writing the icon fails (particularly
                # if doing so would require the user to get a new invite code)
                # so just log a warning for now if something goes wrong...
                resp = yield treq.get(settings['icon_url'])
                if resp.code == 200:
                    content = yield treq.content(resp)
                    log.debug("Received %i bytes", len(content))
                    with open(icon_path, 'wb') as f:
                        f.write(content)
                    self.load_service_icon(icon_path)
                else:
                    log.warning("Error fetching service icon: %i", resp.code)
            except Exception as e:  # pylint: disable=broad-except
                log.warning("Error fetching service icon: %s", str(e))

        while os.path.isdir(os.path.join(config_dir, nickname)):
            title = "{} - Choose a name".format(APP_NAME)
            label = "Please choose a different name for this connection:"
            if nickname:
                label = '{} is already connected to "{}".\n\n{}'.format(
                    APP_NAME, nickname, label)
            nickname, _ = QInputDialog.getText(self, title, label, 0, nickname)

        tahoe = Tahoe(os.path.join(config_dir, nickname))
        self.gateway = tahoe
        yield tahoe.create_client(**settings)
        if icon_path:
            try:
                shutil.copy(icon_path, os.path.join(tahoe.nodedir, 'icon'))
            except OSError as err:
                log.warning("Error copying icon file: %s", str(err))
        if 'icon_url' in settings:
            try:
                with open(os.path.join(tahoe.nodedir, 'icon.url'), 'w') as f:
                    f.write(settings['icon_url'])
            except OSError as err:
                log.warning("Error writing icon url to file: %s", str(err))

        self.update_progress(3, 'Connecting to {}...'.format(nickname))
        yield tahoe.start()

        self.update_progress(4, 'Connecting to {}...'.format(nickname))
        yield tahoe.await_ready()

        self.update_progress(5, 'Generating Recovery Key...')
        yield tahoe.create_rootcap()
        settings_json = os.path.join(tahoe.nodedir, 'private', 'settings.json')
        with open(settings_json, 'w') as f:
            f.write(json.dumps(settings))
        # TODO: Upload, link to rootcap

        self.update_progress(6, 'Done!')
        self.gui.populate([self.gateway])
        self.finish_button.show()

    def show_failure(self, failure):
        log.error(str(failure))
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Retry)
        msg.setEscapeButton(QMessageBox.Retry)
        msg.setDetailedText(str(failure))
        if failure.type == WelcomeError:
            self.show_error("Invite refused")
            msg.setWindowTitle("Invite refused")
            msg.setText(
                "The server negotiating your invitation is online but is "
                "currently refusing to process any invitations. This may "
                "indicate that your version of {} is out-of-date, in which "
                "case you should upgrade to the latest version and try again."
                .format(APP_NAME))
        elif failure.type == WrongPasswordError:
            self.show_error("Invite confirmation failed")
            msg.setWindowTitle("Invite confirmation failed")
            msg.setText(
                "Either you mistyped your invite code or a potential "
                "attacker tried to guess your code and failed. To try "
                "again, you will need to obtain a new invite code from "
                "your inviter.")  # or "service provider"?
        elif failure.type == json.decoder.JSONDecodeError:
            self.show_error("Invalid response")
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Invalid response")
            msg.setText(
                "Your invite code worked but your inviter did not provide "
                "the information needed to complete the invitation process. "
                "Please let them know about the error, and try again later "
                "with a new invite code.")
        elif failure.type == CancelledError and self.page_2.step == 1:
            self.show_error("Invite timed out")
            msg.setWindowTitle("Invite timed out")
            msg.setText(
                "The invitation process has timed out. Your invite code may "
                "have expired. Please request a new invite code from your "
                "inviter and try again.")
        elif failure.type == UpgradeRequiredError:
            self.show_error("Upgrade required")
            msg.setWindowTitle("Upgrade required")
            msg.setText(
                "Your version of {} is out-of-date. Please upgrade to the "
                "latest version and try again with a new invite code.".format(
                    APP_NAME))
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
        elif failure.type == ServerConnectionError:
            self.show_error("Server Connection Error")
            msg.setWindowTitle("Server Connection Error")
            msg.setText(
                "An error occured while connecting to the server. This could "
                "mean that the server is currently down or that there is some "
                "other problem with your connection. Please try again later.")
        else:
            self.show_error(str(failure.type.__name__))
            msg.setWindowTitle(str(failure.type.__name__))
            msg.setText(str(failure.value))
        msg.exec_()
        self.reset()

    def go(self, code):
        self.setCurrentIndex(1)
        self.update_progress(1, 'Verifying invitation code...')
        d = wormhole_receive(code)
        d.addCallback(self.setup)
        d.addErrback(self.show_failure)
        reactor.callLater(60, d.cancel)

    def cancel_button_clicked(self):
        if self.page_2.is_complete():
            self.finish_button_clicked()
            return
        reply = QMessageBox.question(
            self, "Cancel setup?",
            "Are you sure you wish to cancel the {} setup process? "
            "If you do, you may need to obtain a new invite code.".format(
                APP_NAME),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
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
            self.setup(settings)

    def prompt_for_export(self, gateway):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        button_export = msg.button(QMessageBox.Yes)
        button_export.setText("Export...")
        button_skip = msg.button(QMessageBox.No)
        button_skip.setText("Skip")
        msg.setWindowTitle("Export Recovery Key?")
        # "Now that {} is configured..."
        msg.setText(
            "Before uploading any folders to {}, it is <b>strongly "
            "recommended</b> that you <i>export a Recovery Key</i> and store "
            "it in a safe and secure location (such as an encrypted USB drive "
            "that only you have access to).<p><p>A Recovery Key will allow you "
            "to restore any of the folders you've uploaded to {} in the event "
            "that something goes wrong with your computer (e.g., hardware "
            "failure, accidental data-loss, theft, and so on).".format(
                APP_NAME, gateway.name))  # XXX Re-word/improve..
        msg.setDetailedText(
            "A 'Recovery Key' is a small file that contains enough "
            "configuration information to re-establish secure contact with "
            "your cloud storage provider and download your other secret data "
            "keys. Because this file contains secret information "
            "(specifically, your Tahoe-LAFS 'introducer fURL' -- which grants "
            "access to your grid -- and your 'rootcap' -- which grants full "
            "access to all of your uploaded folders), it is important that "
            "you keep this file safe and secure; do not share your Recovery "
            "Key with anybody!")  # XXX Re-word/improve..
        reply = msg.exec_()
        if reply == QMessageBox.Yes:
            self.gui.main_window.export_recovery_key()
        else:
            # TODO: Nag user; "Are you sure?"
            pass

    def finish_button_clicked(self):
        self.gui.show()
        self.close()
        self.prompt_for_export(self.gateway)
        self.reset()

    def closeEvent(self, event):
        if self.gui.main_window.gateways:
            event.accept()
        else:
            event.ignore()
            reply = QMessageBox.question(
                self, "Exit setup?", "{} has not yet been configured. "
                "Are you sure you wish to exit?".format(APP_NAME),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                reactor.stop()
