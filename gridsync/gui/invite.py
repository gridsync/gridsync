# -*- coding: utf-8 -*-

import sys

from PyQt5.QtCore import (
    pyqtSignal, QPropertyAnimation, QSize, QStringListModel, Qt)
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction, QCheckBox, QCompleter, QGraphicsOpacityEffect, QGridLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy, QSpacerItem,
    QWidget)
from twisted.internet import reactor
from twisted.internet.defer import CancelledError, inlineCallbacks
from wormhole.errors import (
    LonelyError, ServerConnectionError, WelcomeError, WrongPasswordError)

from gridsync import resource, APP_NAME
from gridsync.desktop import get_clipboard_modes, get_clipboard_text
from gridsync.errors import UpgradeRequiredError
from gridsync.invite import wordlist, is_valid_code
from gridsync.tor import get_tor


class InviteCodeCompleter(QCompleter):
    def __init__(self):
        super(InviteCodeCompleter, self).__init__()
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.InlineCompletion)

    def pathFromIndex(self, index):
        path = QCompleter.pathFromIndex(self, index)
        words = self.widget().text().split('-')
        if len(words) > 1:
            path = '{}-{}'.format('-'.join(words[:-1]), path)
        return path

    def splitPath(self, path):  # pylint: disable=no-self-use
        return [str(path.split('-')[-1])]


class InviteCodeLineEdit(QLineEdit):

    error = pyqtSignal(str)
    go = pyqtSignal(str)

    def __init__(self, parent=None):
        super(InviteCodeLineEdit, self).__init__()
        self.parent = parent
        model = QStringListModel()
        model.setStringList(wordlist)
        completer = InviteCodeCompleter()
        completer.setModel(model)
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(20)
        else:
            font.setPointSize(16)
        self.setFont(font)
        self.setCompleter(completer)
        self.setAlignment(Qt.AlignCenter)
        #self.setPlaceholderText("Enter invite code")

        self.blank_icon = QIcon()
        self.paste_icon = QIcon(resource('paste.png'))
        self.clear_icon = QIcon(resource('close.png'))
        self.go_icon = QIcon(resource('arrow-right.png'))
        self.tor_icon = QIcon(resource('tor-onion.png'))

        self.status_action = QAction(self.blank_icon, '', self)
        self.addAction(self.status_action, 0)
        self.action_button = QAction(self.blank_icon, '', self)
        self.addAction(self.action_button, 1)

        completer.highlighted.connect(self.update_action_button)
        self.textChanged.connect(self.update_action_button)
        self.returnPressed.connect(self.return_pressed)
        self.action_button.triggered.connect(self.button_clicked)

        self.update_action_button()

    def update_action_button(self, text=None):
        text = (text if text else self.text())
        if not text:
            self.action_button.setIcon(QIcon())
            self.action_button.setToolTip('')
            for mode in get_clipboard_modes():
                if is_valid_code(get_clipboard_text(mode)):
                    self.action_button.setIcon(self.paste_icon)
                    self.action_button.setToolTip("Paste")
        elif is_valid_code(text):
            self.action_button.setIcon(self.go_icon)
            self.action_button.setToolTip("Go")
        else:
            self.action_button.setIcon(self.clear_icon)
            self.action_button.setToolTip("Clear")

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
        return None

    def return_pressed(self):
        code = self.text().lower()
        if is_valid_code(code):
            self.go.emit(code)
        else:
            self.error.emit("Invalid code")

    def button_clicked(self):
        code = self.text().lower()
        if not code:
            for mode in get_clipboard_modes():
                text = get_clipboard_text(mode)
                if is_valid_code(text):
                    self.setText(text)
        elif is_valid_code(code):
            self.go.emit(code)
        else:
            self.setText('')


class InviteCodeWidget(QWidget):
    def __init__(self, parent=None, tor_available=False):
        super(InviteCodeWidget, self).__init__()
        self.parent = parent

        self.label = QLabel("Enter invite code:")
        font = QFont()
        if sys.platform == 'darwin':
            font.setPointSize(18)
        else:
            font.setPointSize(14)
        self.label.setFont(font)
        self.label.setStyleSheet("color: grey")
        self.label.setAlignment(Qt.AlignCenter)

        self.code_info_text = (
            'An <i>invite code</i> is a short combination of numbers and '
            'words (like "7-guitarist-revenge" or "9-potato-gremlin") that '
            'allows two parties with the same code to establish a one-time '
            'secure communication channel with each other. In Gridsync, '
            'invite codes are used to safely share the credentials needed '
            'to access resources -- for example, allowing another person or '
            'device to store files on a grid or granting them the ability to '
            'view and modify a folder.<p>'
            'Invite codes can only be used once and expire immediately when '
            'used or cancelled.'
        )
        self.code_info_button = QPushButton()
        self.code_info_button.setFlat(True)
        self.code_info_button.setIcon(QIcon(resource('question')))
        self.code_info_button.setIconSize(QSize(13, 13))
        if sys.platform == 'darwin':
            self.code_info_button.setFixedSize(16, 16)
        else:
            self.code_info_button.setFixedSize(13, 13)
        self.code_info_button.setToolTip(self.code_info_text)
        self.code_info_button.clicked.connect(self.on_code_info_button_clicked)
        self.code_info_button.setFocusPolicy(Qt.NoFocus)

        label_layout = QGridLayout()
        label_layout.setHorizontalSpacing(6)
        label_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        label_layout.addWidget(self.label, 1, 2, Qt.AlignCenter)
        label_layout.addWidget(self.code_info_button, 1, 3, Qt.AlignLeft)
        label_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 5)

        self.lineedit = InviteCodeLineEdit(self)

        self.tor_checkbox = QCheckBox("Connect over the Tor network")
        if sys.platform == 'darwin':
            # For some reason, the checkbox and pushbutton overlap slightly on
            # macOS. A space here adds just enough padding to separate them.
            self.tor_checkbox.setText(self.tor_checkbox.text() + ' ')
        self.tor_checkbox.setStyleSheet("QCheckBox { color: dimgrey }")
        self.tor_checkbox.setFocusPolicy(Qt.NoFocus)
        self.tor_checkbox_effect = QGraphicsOpacityEffect()
        self.tor_checkbox.setGraphicsEffect(self.tor_checkbox_effect)
        self.tor_checkbox.setAutoFillBackground(True)

        self.tor_checkbox_animation_in = QPropertyAnimation(
            self.tor_checkbox_effect, b'opacity')
        self.tor_checkbox_animation_in.setDuration(500)
        self.tor_checkbox_animation_in.setStartValue(0)
        self.tor_checkbox_animation_in.setEndValue(1)

        self.tor_checkbox_animation_out = QPropertyAnimation(
            self.tor_checkbox_effect, b'opacity')
        self.tor_checkbox_animation_out.setDuration(500)
        self.tor_checkbox_animation_out.setStartValue(1)
        self.tor_checkbox_animation_out.setEndValue(0)

        self.tor_info_text = (
            "<i>Tor</i> is an anonymizing network that helps defend against "
            "network surveillance and traffic analysis. With this checkbox "
            "enabled, {} will route all traffic corresponding to this "
            "connection through the Tor network, concealing your geographical "
            "location from your storage provider and other parties (such as "
            "any persons with whom you might share folders).<p>"
            "Using this option requires that Tor already be installed and "
            "running on your computer and may be slower or less reliable than "
            "your normal internet connection.<p>"
            "For more information or to download Tor, please visit "
            "<a href=https://torproject.org>https://torproject.org</a>".format(
                APP_NAME)
        )
        self.tor_info_button = QPushButton()
        self.tor_info_button.setFlat(True)
        self.tor_info_button.setIcon(QIcon(resource('question')))
        self.tor_info_button.setIconSize(QSize(13, 13))
        if sys.platform == 'darwin':
            self.tor_info_button.setFixedSize(16, 16)
        else:
            self.tor_info_button.setFixedSize(13, 13)
        self.tor_info_button.setToolTip(self.tor_info_text)
        self.tor_info_button.clicked.connect(self.on_tor_info_button_clicked)
        self.tor_info_button.setFocusPolicy(Qt.NoFocus)
        self.tor_info_button_effect = QGraphicsOpacityEffect()
        self.tor_info_button.setGraphicsEffect(self.tor_info_button_effect)
        self.tor_info_button.setAutoFillBackground(True)

        self.tor_info_button_animation_in = QPropertyAnimation(
            self.tor_info_button_effect, b'opacity')
        self.tor_info_button_animation_in.setDuration(500)
        self.tor_info_button_animation_in.setStartValue(0)
        self.tor_info_button_animation_in.setEndValue(1)

        self.tor_info_button_animation_out = QPropertyAnimation(
            self.tor_info_button_effect, b'opacity')
        self.tor_info_button_animation_out.setDuration(500)
        self.tor_info_button_animation_out.setStartValue(1)
        self.tor_info_button_animation_out.setEndValue(0)

        if tor_available:
            self.tor_checkbox_effect.setOpacity(1.0)
            self.tor_info_button_effect.setOpacity(1.0)
        else:
            self.tor_checkbox.setEnabled(False)
            self.tor_checkbox_effect.setOpacity(0.0)
            self.tor_info_button_effect.setOpacity(0.0)

        tor_layout = QGridLayout()
        tor_layout.setHorizontalSpacing(0)
        tor_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1)
        tor_layout.addWidget(self.tor_checkbox, 1, 2, Qt.AlignCenter)
        tor_layout.addWidget(self.tor_info_button, 1, 3, Qt.AlignLeft)
        tor_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 4)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 1, 1)
        layout.addLayout(label_layout, 2, 1)
        layout.addWidget(self.lineedit, 3, 1)
        layout.addLayout(tor_layout, 4, 1)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 5, 1)

        self.tor_checkbox.toggled.connect(self.toggle_tor_status)

        self.maybe_enable_tor_checkbox()

    @inlineCallbacks
    def maybe_enable_tor_checkbox(self):
        tor = yield get_tor(reactor)
        if tor and not self.tor_checkbox.isEnabled():
            self.tor_checkbox.setEnabled(True)
            self.tor_checkbox_animation_in.start()
            self.tor_info_button_animation_in.start()
        elif not tor and self.tor_checkbox.isEnabled():
            self.tor_checkbox.setEnabled(False)
            self.tor_checkbox_animation_out.start()
            self.tor_info_button_animation_out.start()

    def toggle_tor_status(self, state):
        if state:
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Warning)
            title = "Enable Tor?"
            text = (
                "Tor support in {} is currently <i>experimental</i> and may "
                "contain serious bugs that could jeopardize your anonymity.<p>"
                "Are you sure you wish to enable Tor for this connection?<br>"
                .format(APP_NAME)
            )
            if sys.platform == 'darwin':
                msgbox.setText(title)
                msgbox.setInformativeText(text)
            else:
                msgbox.setWindowTitle(title)
                msgbox.setText(text)
            checkbox = QCheckBox(
                "I understand and accept the risks. Enable Tor.")
            msgbox.setCheckBox(checkbox)
            msgbox.setWindowModality(Qt.ApplicationModal)
            msgbox.exec_()
            if not checkbox.isChecked():
                self.tor_checkbox.setChecked(False)
                return
            self.lineedit.status_action.setIcon(self.lineedit.tor_icon)
            self.lineedit.status_action.setToolTip(
                "Tor: Enabled\n\n"
                "This connection will be routed through the Tor network.")
            #self.lineedit.setStyleSheet(
            #    "border-width: 1px;"
            #    "border-style: solid;"
            #    "border-color: {0};"
            #    "border-radius: 2px;"
            #    "padding: 2px;"
            #    "color: {0};".format(TOR_DARK_PURPLE))
        else:
            self.lineedit.status_action.setIcon(self.lineedit.blank_icon)
            self.lineedit.status_action.setToolTip("")
            #self.lineedit.setStyleSheet("")

    def on_tor_info_button_clicked(self):
        msgbox = QMessageBox(self)
        msgbox.setIconPixmap(self.lineedit.tor_icon.pixmap(64, 64))
        if sys.platform == 'darwin':
            msgbox.setText("About Tor")
            msgbox.setInformativeText(self.tor_info_text)
        else:
            msgbox.setWindowTitle("About Tor")
            msgbox.setText(self.tor_info_text)
        msgbox.show()

    def on_code_info_button_clicked(self):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        text = (
            '{}<p><a href=https://github.com/gridsync/gridsync/blob/master/doc'
            's/invite-codes.md>Learn more...</a>'.format(self.code_info_text)
        )
        if sys.platform == 'darwin':
            msgbox.setText("About Invite Codes")
            msgbox.setInformativeText(text)
        else:
            msgbox.setWindowTitle("About Invite Codes")
            msgbox.setText(text)
        msgbox.show()


def show_failure(failure, parent=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setStandardButtons(QMessageBox.Retry)
    msg.setEscapeButton(QMessageBox.Retry)
    msg.setDetailedText(str(failure))
    if failure.type == ServerConnectionError:
        msg.setWindowTitle("Server Connection Error")
        msg.setText("An error occured while connecting to the invite server.")
        msg.setInformativeText(
            "This could mean that it is currently offline or that there is "
            "some other problem with your connection. Please try again later.")
    elif failure.type == WelcomeError:
        msg.setWindowTitle("Invite refused")
        msg.setText(
            "The server negotiating your invitation is refusing to process "
            "any invitations.")
        msg.setInformativeText(
            "This may indicate that your version of {} is out-of-date, in "
            "which case you should upgrade to the latest version and try "
            "again.".format(APP_NAME))
        msg.setIcon(QMessageBox.Critical)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setEscapeButton(QMessageBox.Ok)
    elif failure.type == WrongPasswordError:
        msg.setWindowTitle("Invite confirmation failed")
        msg.setText("Invite confirmation failed")
        msg.setInformativeText(
            "Either your recipient mistyped the invite code or a potential "
            "attacker tried to guess the code and failed.\n\nTo try again, "
            "you will need a new invite code.")
    elif failure.type == LonelyError:  # Raises only when closing(?)
        return
    elif failure.type == UpgradeRequiredError:
        msg.setWindowTitle("Upgrade required")
        msg.setText("Your version of {} is out-of-date.".format(APP_NAME))
        msg.setInformativeText(
            "Please upgrade to the latest version and try again with a new "
            "invite code.")
        msg.setIcon(QMessageBox.Critical)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setEscapeButton(QMessageBox.Ok)
    elif failure.type == CancelledError:
        msg.setWindowTitle("Invite timed out")
        msg.setText("The invitation process has timed out.")
        msg.setInformativeText(
            "Your invite code may have expired. Please request a new invite "
            "code from the other party and try again.")
    else:
        msg.setWindowTitle(str(failure.type.__name__))
        msg.setText(str(failure.value))
    msg.exec_()
