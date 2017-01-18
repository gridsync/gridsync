# -*- coding: utf-8 -*-

import json
import os

from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QCompleter, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError, inlineCallbacks
from wormhole.errors import WrongPasswordError
from wormhole.wordlist import raw_words
from wormhole.xfer_util import receive

from gridsync import config_dir
from gridsync import settings as global_settings
from gridsync.resource import resource
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
    else:
        return True


class Completer(QCompleter):
    def __init__(self):
        super(self.__class__, self).__init__()
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
        super(self.__class__, self).__init__()
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

    def keyPressEvent(self, event):
        key = event.key()
        text = self.text()
        if key == Qt.Key_Space:
            if text and not text.endswith('-'):
                self.setText(text + '-')
        elif key == Qt.Key_Tab:
            if text and len(text.split('-')) < 3 and not text.endswith('-'):
                self.setText(text + '-')
            else:
                self.setText(text)
        elif key == Qt.Key_Escape:
            if text:
                self.parent.reset()
            else:
                self.parent.close()
        else:
            return QLineEdit.keyPressEvent(self, event)


class InviteForm(QWidget):
    def __init__(self):  # pylint: disable=too-many-statements
        super(self.__class__, self).__init__()
        self.step = 0
        self.resize(500, 333)
        layout = QVBoxLayout(self)

        layout_1 = QHBoxLayout()
        self.icon = QLabel()
        pixmap = QPixmap(resource('mail-envelope-open.png')).scaled(128, 128)
        self.icon.setPixmap(pixmap)
        layout_1.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))
        layout_1.addWidget(self.icon)
        layout_1.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))

        layout_2 = QHBoxLayout()
        self.label = QLabel("Enter invite code:")
        font = QFont()
        font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: grey")
        layout_2.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))
        layout_2.addWidget(self.label)
        layout_2.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))

        layout_3 = QHBoxLayout()
        self.lineedit = LineEdit(self)
        self.lineedit.returnPressed.connect(self.return_pressed)
        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(8)
        self.progressbar.setTextVisible(False)
        self.progressbar.hide()
        layout_3.addItem(QSpacerItem(85, 0, QSizePolicy.Preferred, 0))
        layout_3.addWidget(self.lineedit)
        layout_3.addWidget(self.progressbar)
        layout_3.addItem(QSpacerItem(85, 0, QSizePolicy.Preferred, 0))

        layout_4 = QHBoxLayout()
        self.checkbox = QCheckBox(self)
        self.checkbox.setText("Always connect using Tor")
        self.checkbox.setEnabled(True)
        self.checkbox.setCheckable(False)
        self.checkbox.setStyleSheet("color: grey")
        self.checkbox.setFocusPolicy(Qt.NoFocus)
        self.message = QLabel()
        self.message.hide()
        layout_4.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))
        layout_4.addWidget(self.checkbox)
        layout_4.addWidget(self.message)
        layout_4.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0))

        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        layout.addLayout(layout_1)
        layout.addLayout(layout_2)
        layout.addLayout(layout_3)
        layout.addLayout(layout_4)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))

    def update_progress(self, step, message):
        self.step = step
        self.progressbar.setValue(step)
        self.progressbar.show()
        self.message.setStyleSheet("color: grey")
        self.message.setText(message)
        self.message.show()

    def show_error(self, message):
        self.message.setStyleSheet("color: red")
        self.message.setText(message)
        self.checkbox.hide()
        self.message.show()
        reactor.callLater(3, self.message.hide)
        reactor.callLater(3, self.checkbox.show)

    @inlineCallbacks
    def setup(self, settings):
        settings = json.loads(settings)
        folder = os.path.join(os.path.expanduser('~'), 'Private')
        try:
            os.makedirs(folder)
        except OSError:
            pass

        self.update_progress(2, 'Creating gateway...')
        tahoe = Tahoe(os.path.join(config_dir, 'default'))
        args = ['create-client', '--webport=tcp:0:interface=127.0.0.1']
        for option in ('nickname', 'introducer'):
            # TODO: Add 'needed', 'happy', 'total' pending tahoe-lafs PR #376
            # https://github.com/tahoe-lafs/tahoe-lafs/pull/376
            if option in settings:
                args.extend(['--{}'.format(option), settings[option]])
        yield tahoe.command(args)

        self.update_progress(3, 'Configuring gateway...')
        for option in ('needed', 'happy', 'total'):
            if option in settings:
                tahoe.config_set('client', 'shares.{}'.format(option),
                                 settings[option])

        self.update_progress(4, 'Starting gateway...')
        yield tahoe.start()

        self.update_progress(5, 'Connecting to grid...')
        # TODO: Replace with call to "readiness" API?
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2844
        yield tahoe.await_ready()

        self.update_progress(6, 'Creating magic-folder...')
        yield tahoe.command(['magic-folder', 'create', 'magic:', 'admin',
                             folder])

        self.update_progress(7, 'Reloading...')
        yield tahoe.start()

        self.update_progress(8, 'Done!')
        yield tahoe.await_ready()
        # TODO: Open local folder with file manager instead?
        yield tahoe.command(['webopen'])
        self.close()

    def reset(self):
        self.update_progress(0, '')
        self.label.setText("Enter invite code:")
        self.lineedit.setText('')
        self.progressbar.hide()
        self.message.hide()
        self.lineedit.show()
        self.checkbox.show()

    def show_failure(self, failure):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Retry)
        msg.setEscapeButton(QMessageBox.Retry)
        msg.setDetailedText(str(failure))
        if failure.type == WrongPasswordError:
            self.show_error("Invite confirmation failed")
            msg.setWindowTitle("Invite confirmation failed")
            msg.setText(
                "Either you mistyped your invite code, or a potential "
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
        elif failure.type == CancelledError and self.step == 1:
            self.show_error("Invite timed out")
            msg.setWindowTitle("Invite timed out")
            msg.setText(
                "The invitation process has timed out. Your invite code may "
                "have expired. Please request a new invite code from your "
                "inviter and try again.")
        # XXX: Other errors?
        else:
            return
        msg.exec_()
        self.reset()

    def return_pressed(self):
        code = self.lineedit.text().lower()
        if is_valid(code):
            self.label.setText('')
            self.lineedit.hide()
            self.checkbox.hide()
            self.update_progress(1, 'Opening wormhole...')
            d = receive(reactor, global_settings['wormhole']['appid'],
                        global_settings['wormhole']['relay'], code)
            d.addCallback(self.setup)
            d.addErrback(self.show_failure)
            reactor.callLater(5, d.cancel)
        else:
            self.show_error("Invalid code")
