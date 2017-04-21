# -*- coding: utf-8 -*-

import base64
import json
import logging as log
import os
import shutil
import tempfile

from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction, QCheckBox, QCompleter, QGridLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QProgressBar, QSizePolicy, QSpacerItem,
    QStackedWidget, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError, inlineCallbacks
from wormhole.errors import WelcomeError, WrongPasswordError
from wormhole.wordlist import raw_words
from wormhole.xfer_util import receive

from gridsync import config_dir, resource
from gridsync import settings as global_settings
from gridsync.desktop import get_clipboard_modes, get_clipboard_text
from gridsync.tahoe import Tahoe


wordlist = []
for word in raw_words.items():
    wordlist.extend(word[1])
wordlist = sorted([word.lower() for word in wordlist])


def is_valid(code):
    words = code.split('-')
    if len(words) != 3:
        return False
    elif not words[0].isdigit():
        return False
    elif not words[1] in wordlist:
        return False
    elif not words[2] in wordlist:
        return False
    return True


class UpgradeRequiredError(Exception):
    pass


class Completer(QCompleter):
    def __init__(self):
        super(Completer, self).__init__()
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setMaxVisibleItems(5)
        #self.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompletionMode(QCompleter.InlineCompletion)

    def pathFromIndex(self, index):
        path = QCompleter.pathFromIndex(self, index)
        words = self.widget().text().split('-')
        if len(words) > 1:
            path = '{}-{}'.format('-'.join(words[:-1]), path)
        return path

    def splitPath(self, path):  # pylint: disable=no-self-use
        return [str(path.split('-')[-1])]


class LineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(LineEdit, self).__init__()
        self.parent = parent
        font = QFont()
        font.setPointSize(16)
        model = QStringListModel()
        model.setStringList(wordlist)
        completer = Completer()
        completer.setModel(model)
        self.setFont(font)
        self.setCompleter(completer)
        self.setAlignment(Qt.AlignCenter)
        #self.setPlaceholderText("Enter invite code")
        self.button_action = QAction(QIcon(), '', self)
        self.addAction(self.button_action, 1)
        self.addAction(QAction(QIcon(), '', self), 0)  # for symmetry

        completer.highlighted.connect(self.update_button)
        self.textChanged.connect(self.update_button)

        self.update_button()

    def update_button(self, text=None):
        text = (text if text else self.text())
        if not text:
            self.button_action.setIcon(QIcon())
            self.button_action.setToolTip('')
            for mode in get_clipboard_modes():
                if is_valid(get_clipboard_text(mode)):
                    self.button_action.setIcon(QIcon(resource('paste.png')))
                    self.button_action.setToolTip("Paste")
        elif is_valid(text):
            self.button_action.setIcon(QIcon(resource('arrow-right.png')))
            self.button_action.setToolTip("Go")
        else:
            self.button_action.setIcon(QIcon(resource('close.png')))
            self.button_action.setToolTip("Clear")

    def keyPressEvent(self, event):
        key = event.key()
        text = self.text()
        if key in (Qt.Key_Space, Qt.Key_Minus, Qt.Key_Tab):
            if text and len(text.split('-')) < 3 and not text.endswith('-'):
                self.setText(text + '-')
            else:
                self.setText(text)
        elif text and key == Qt.Key_Escape:
            self.setText('')
        else:
            return QLineEdit.keyPressEvent(self, event)


class CodeEntryWidget(QWidget):
    def __init__(self, parent=None):
        super(CodeEntryWidget, self).__init__()
        self.parent = parent

        self.icon = QLabel()
        pixmap = QPixmap(resource('gridsync.png')).scaled(220, 220)
        self.icon.setPixmap(pixmap)
        self.icon.setAlignment(Qt.AlignCenter)

        self.slogan = QLabel("<i>Encrypted, distributed storage</i>")
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

        self.lineedit = LineEdit(self)

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
        pixmap = QPixmap(resource('laptop.png')).scaled(128, 128)
        self.icon_client.setPixmap(pixmap)
        self.icon_client.setAlignment(Qt.AlignCenter)

        self.checkmark = QLabel()
        pixmap = QPixmap(resource('pixel.png')).scaled(32, 32)
        self.checkmark.setPixmap(pixmap)
        self.checkmark.setAlignment(Qt.AlignCenter)

        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(5)
        self.progressbar.setTextVisible(False)

        self.message = QLabel()
        self.message.setStyleSheet("color: grey")
        self.message.setAlignment(Qt.AlignCenter)

        self.finish_button = QPushButton("Finish")
        self.finish_button.hide()

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 0, 0)
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

    def reset(self):
        self.update_progress(0, '')


class InviteForm(QStackedWidget):
    def __init__(self, gui):
        super(InviteForm, self).__init__()
        self.gui = gui
        self.gateway = None
        self.resize(400, 500)
        self.setWindowTitle(global_settings['application']['name'])
        self.page_1 = CodeEntryWidget(self)
        self.page_2 = ProgressBarWidget()

        self.addWidget(self.page_1)
        self.addWidget(self.page_2)

        self.lineedit = self.page_1.lineedit
        self.button_action = self.lineedit.button_action
        self.finish_button = self.page_2.finish_button

        self.lineedit.returnPressed.connect(self.return_pressed)
        self.button_action.triggered.connect(self.button_clicked)
        self.finish_button.clicked.connect(self.finish_button_clicked)

    def update_progress(self, step, message):
        self.page_2.update_progress(step, message)

    def show_error(self, message):
        self.page_1.show_error(message)

    def reset(self):
        self.page_1.reset()
        self.page_2.reset()
        self.setCurrentIndex(0)

    @inlineCallbacks
    def setup(self, settings):
        settings = json.loads(settings)

        if 'version' in settings and int(settings['version']) > 1:
            raise UpgradeRequiredError

        if 'nickname' in settings:
            nickname = settings['nickname']
        else:
            nickname = settings['introducer'].split('@')[1].split(':')[0]

        self.update_progress(2, 'Connecting to {}...'.format(nickname))
        if 'icon_base64' in settings:
            temp = tempfile.NamedTemporaryFile()
            temp.write(base64.b64decode(settings['icon_base64']))
            pixmap = QPixmap(temp.name).scaled(100, 100)
            self.page_2.icon_overlay.setPixmap(pixmap)

        pixmap = QPixmap(resource('lines_dotted.png')).scaled(128, 128)
        self.page_2.icon_connection.setPixmap(pixmap)
        pixmap = QPixmap(resource('cloud_storage.png')).scaled(220, 220)
        self.page_2.icon_server.setPixmap(pixmap)
        tahoe = Tahoe(os.path.join(config_dir, nickname))
        self.gateway = tahoe
        yield tahoe.create_client(**settings)
        if 'icon_base64' in settings:
            shutil.copy2(temp.name, os.path.join(tahoe.nodedir, 'icon'))

        self.update_progress(3, 'Connecting to {}...'.format(nickname))
        yield tahoe.start()

        self.update_progress(4, 'Connecting to {}...'.format(nickname))
        yield tahoe.await_ready()

        self.update_progress(5, 'Done!')
        pixmap = QPixmap(resource('lines_solid.png')).scaled(128, 128)
        self.page_2.icon_connection.setPixmap(pixmap)
        pixmap = QPixmap(resource('green_checkmark.png')).scaled(32, 32)
        self.page_2.checkmark.setPixmap(pixmap)
        self.gui.populate([self.gateway])
        self.finish_button.show()

    def show_failure(self, failure):
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
                .format(global_settings['application']['name']))
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
                    global_settings['application']['name']))
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
        else:
            log.error(str(failure))
            return
        msg.exec_()
        self.reset()

    def go(self, code):
        self.setCurrentIndex(1)
        self.update_progress(1, 'Verifying invitation code...')
        d = receive(reactor, global_settings['wormhole']['appid'],
                    global_settings['wormhole']['relay'], code)
        d.addCallback(self.setup)
        d.addErrback(self.show_failure)
        reactor.callLater(20, d.cancel)

    def return_pressed(self):
        code = self.lineedit.text().lower()
        if is_valid(code):
            self.go(code)
        else:
            self.show_error("Invalid code")

    def button_clicked(self):
        code = self.lineedit.text().lower()
        if not code:
            for mode in get_clipboard_modes():
                text = get_clipboard_text(mode)
                if is_valid(text):
                    self.lineedit.setText(text)
        elif is_valid(code):
            self.go(code)
        else:
            self.reset()

    def finish_button_clicked(self):
        self.gui.show()
        self.close()
