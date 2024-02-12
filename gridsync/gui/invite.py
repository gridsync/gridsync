# -*- coding: utf-8 -*-
import logging
import os
import sys
from typing import Optional, cast

from qtpy.QtCore import (
    QModelIndex,
    QPropertyAnimation,
    QStringListModel,
    Qt,
    QTimer,
    Signal,
)
from qtpy.QtGui import QFont, QIcon, QKeyEvent
from qtpy.QtWidgets import (
    QAction,
    QCheckBox,
    QCompleter,
    QGraphicsOpacityEffect,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QToolButton,
    QWidget,
)
from twisted.internet import reactor as reactor_module
from twisted.internet.defer import CancelledError, inlineCallbacks
from twisted.internet.interfaces import IReactorCore
from twisted.python.failure import Failure
from wormhole.errors import (
    LonelyError,
    ServerConnectionError,
    WelcomeError,
    WrongPasswordError,
)

from gridsync import APP_NAME, resource
from gridsync.desktop import (
    get_clipboard_modes,
    get_clipboard_text,
    set_clipboard_text,
)
from gridsync.errors import UpgradeRequiredError
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.widgets import HSpacer, InfoButton, VSpacer
from gridsync.invite import is_valid_code, wordlist
from gridsync.tor import get_tor
from gridsync.types_ import TwistedDeferred
from gridsync.util import b58encode

# mypy thinks reactor is a module
# https://github.com/twisted/twisted/issues/9909
reactor = cast(IReactorCore, reactor_module)


class InviteCodeCompleter(QCompleter):
    def __init__(self) -> None:
        super().__init__()
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.InlineCompletion)

    def pathFromIndex(self, index: QModelIndex) -> str:
        path = QCompleter.pathFromIndex(self, index)
        words = self.widget().text().split("-")  # type: ignore
        if len(words) > 1:
            path = "{}-{}".format("-".join(words[:-1]), path)
        return path

    def splitPath(self, path: str) -> list[str]:
        return [str(path.split("-")[-1])]


class InviteHeaderWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.icon_label = QLabel(self)

        self.text_label = QLabel(self)
        self.text_label.setFont(Font(18))
        self.text_label.setAlignment(Qt.AlignCenter)

        layout = QGridLayout(self)
        layout.addItem(HSpacer(), 1, 1)
        layout.addWidget(self.icon_label, 1, 2)
        layout.addWidget(self.text_label, 1, 3)
        layout.addItem(HSpacer(), 1, 4)

    def set_icon(self, icon: QIcon) -> None:
        self.icon_label.setPixmap(icon.pixmap(50, 50))

    def set_text(self, text: str) -> None:
        self.text_label.setText(text)


class InviteCodeBox(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.noise_label = QLabel()
        font = Font(16)
        if sys.platform == "darwin":
            # "Courier" was removed from macOS 13
            font.setFamily("Courier New")
        else:
            font.setFamily("Courier")
        font.setStyleHint(QFont.Monospace)
        self.noise_label.setFont(font)
        self.noise_label.setStyleSheet("color: grey")

        self.noise_timer = QTimer()
        self.noise_timer.timeout.connect(
            lambda: self.noise_label.setText(b58encode(os.urandom(16)))
        )

        self.code_label = QLabel()
        self.code_label.setFont(Font(18))
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code_label.hide()

        self.box = QGroupBox()
        self.box.setAlignment(Qt.AlignCenter)
        self.box.setStyleSheet("QGroupBox {font-size: 16px}")

        # QGroupBox's built-in title is unavailable on macOS, so
        # instantiate a QLabel that we can use to simulate one...
        self.box_title = QLabel(self)
        self.box_title.setAlignment(Qt.AlignCenter)
        self.box_title.setFont(Font(16))

        self.copy_button = QToolButton()
        self.copy_button.setIcon(QIcon(resource("copy.png")))
        self.copy_button.setToolTip("Copy to clipboard")
        self.copy_button.setStyleSheet("border: 0px; padding: 0px;")
        self.copy_button.clicked.connect(self._on_copy_button_clicked)
        self.copy_button.hide()

        box_layout = QGridLayout(self.box)
        box_layout.addItem(HSpacer(), 1, 1)
        box_layout.addWidget(self.noise_label, 1, 2)
        box_layout.addWidget(self.code_label, 1, 3)
        box_layout.addWidget(self.copy_button, 1, 4)
        box_layout.addItem(HSpacer(), 1, 5)

        layout = QGridLayout(self)
        if sys.platform == "darwin":
            layout.addWidget(self.box_title)
        layout.addWidget(self.box)

    def set_title(self, text: str) -> None:
        if sys.platform == "darwin":
            self.box_title.setText(text)
            self.box_title.show()
        else:
            self.box.setTitle(text)

    def show_noise(self) -> None:
        self.code_label.setText("")
        self.code_label.hide()
        self.copy_button.hide()
        self.set_title("Generating invite code...")
        self.noise_timer.start(75)
        self.noise_label.show()

    def show_code(self, code: str) -> None:
        self.noise_timer.stop()
        self.noise_label.hide()
        self.set_title("Your invite code is:")
        self.code_label.setText(code)
        self.code_label.show()
        self.copy_button.show()

    def get_code(self) -> str:
        return self.code_label.text()

    def _on_copy_button_clicked(self) -> None:
        code = self.get_code()
        for mode in get_clipboard_modes():
            set_clipboard_text(code, mode)


class InviteCodeLineEdit(QLineEdit):
    error = Signal(str)
    go = Signal(str)
    code_cleared = Signal()
    code_validated = Signal(str)
    code_invalidated = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        model = QStringListModel()
        model.setStringList(wordlist)
        completer = InviteCodeCompleter()
        completer.setModel(model)
        self.setFont(Font(16))
        self.setCompleter(completer)
        self.setAlignment(Qt.AlignCenter)
        # self.setPlaceholderText("Enter invite code")

        self.blank_icon = QIcon()
        self.paste_icon = QIcon(resource("paste.png"))
        self.clear_icon = QIcon(resource("close.png"))
        self.go_icon = QIcon(resource("arrow-right.png"))
        self.tor_icon = QIcon(resource("tor-onion.png"))

        self.status_action = QAction(self.blank_icon, "", self)
        self.addAction(self.status_action, QLineEdit.LeadingPosition)
        self.action_button = QAction(self.blank_icon, "", self)
        self.addAction(self.action_button, QLineEdit.TrailingPosition)

        completer.highlighted.connect(self.update_action_button)
        self.textChanged.connect(self.update_action_button)
        self.returnPressed.connect(self.return_pressed)
        self.action_button.triggered.connect(self.button_clicked)

        self.update_action_button()

    def update_action_button(self, text: Optional[str] = None) -> None:
        text = text if text else self.text()
        if not text:
            self.action_button.setIcon(QIcon())
            self.action_button.setToolTip("")
            for mode in get_clipboard_modes():
                clipboard_text = get_clipboard_text(mode)
                if clipboard_text and is_valid_code(clipboard_text):
                    self.action_button.setIcon(self.paste_icon)
                    self.action_button.setToolTip("Paste")
        elif is_valid_code(text):
            self.action_button.setIcon(self.go_icon)
            self.action_button.setToolTip("Go")
            self.code_validated.emit(text)
        else:
            self.action_button.setIcon(self.clear_icon)
            self.action_button.setToolTip("Clear")
            self.code_invalidated.emit(text)

    def keyPressEvent(self, event: QKeyEvent) -> Optional[QKeyEvent]:  # type: ignore
        # mypy: 'incompatible with return type "None" in supertype "QLineEdit"'
        # mypy: 'incompatible with return type "None" in supertype "QWidget"'
        key = event.key()
        text = self.text()
        if key in (Qt.Key_Space, Qt.Key_Minus, Qt.Key_Tab):
            if text and len(text.split("-")) < 3 and not text.endswith("-"):
                self.setText(text + "-")
            else:
                self.setText(text)
        elif text and key == Qt.Key_Escape:
            self.setText("")
            self.code_cleared.emit()
        else:
            return QLineEdit.keyPressEvent(self, event)
        return None

    def return_pressed(self) -> None:
        code = self.text().lower()
        if is_valid_code(code):
            self.go.emit(code)
        else:
            self.error.emit("Invalid code")

    def button_clicked(self) -> None:
        code = self.text().lower()
        if not code:
            for mode in get_clipboard_modes():
                text = get_clipboard_text(mode)
                if text and is_valid_code(text):
                    self.setText(text)
        elif is_valid_code(code):
            self.go.emit(code)
        else:
            self.setText("")


class InviteCodeWidget(QWidget):
    code_cleared = Signal()
    code_entered = Signal(str)
    code_validated = Signal(str)
    code_invalidated = Signal(str)
    error_occurred = Signal(str)

    def __init__(
        self, parent: Optional[QWidget] = None, tor_available: bool = False
    ) -> None:
        super().__init__(parent)
        self.label = QLabel("Enter invite code:")
        self.label.setFont(Font(14))
        p = self.palette()
        dimmer_grey = BlendedColor(
            p.windowText().color(), p.window().color()
        ).name()
        self.label.setStyleSheet("color: {}".format(dimmer_grey))

        self.label.setAlignment(Qt.AlignCenter)

        self.code_info_button = InfoButton(
            "About Invite Codes",
            "An <i>invite code</i> is a short combination of numbers and "
            'words (like "7-guitarist-revenge") that allows two parties with '
            "the same code to establish a one-time secure communication "
            "channel with each other.<p>"
            f"In {APP_NAME}, invite codes are used to safely exchange the "
            "credentials needed to access resources -- for example, to grant "
            "another device the ability to view and modify a folder<p>"
            "Invite codes can only be used once and expire immediately when "
            "used or cancelled.",
            self,
        )

        label_layout = QGridLayout()
        label_layout.setHorizontalSpacing(6)
        label_layout.addItem(HSpacer(), 1, 1)
        label_layout.addWidget(self.label, 1, 2, Qt.AlignCenter)
        label_layout.addWidget(self.code_info_button, 1, 3, Qt.AlignLeft)
        label_layout.addItem(HSpacer(), 1, 5)

        self.lineedit = InviteCodeLineEdit(self)
        self.lineedit.go.connect(self.code_entered)
        self.lineedit.error.connect(self.error_occurred)
        self.lineedit.code_cleared.connect(self.code_cleared)
        self.lineedit.code_validated.connect(self.code_validated)
        self.lineedit.code_invalidated.connect(self.code_invalidated)

        self.tor_checkbox = QCheckBox("Connect over the Tor network")
        if sys.platform == "darwin":
            # For some reason, the checkbox and pushbutton overlap slightly on
            # macOS. A space here adds just enough padding to separate them.
            self.tor_checkbox.setText(self.tor_checkbox.text() + " ")
        self.tor_checkbox.setStyleSheet("QCheckBox { color: dimgrey }")
        self.tor_checkbox.setFocusPolicy(Qt.NoFocus)
        self.tor_checkbox_effect = QGraphicsOpacityEffect()
        self.tor_checkbox.setGraphicsEffect(self.tor_checkbox_effect)
        self.tor_checkbox.setAutoFillBackground(True)

        self.tor_checkbox_animation_in = QPropertyAnimation(
            self.tor_checkbox_effect, b"opacity"
        )
        self.tor_checkbox_animation_in.setDuration(500)
        self.tor_checkbox_animation_in.setStartValue(0)
        self.tor_checkbox_animation_in.setEndValue(1)

        self.tor_checkbox_animation_out = QPropertyAnimation(
            self.tor_checkbox_effect, b"opacity"
        )
        self.tor_checkbox_animation_out.setDuration(500)
        self.tor_checkbox_animation_out.setStartValue(1)
        self.tor_checkbox_animation_out.setEndValue(0)

        self.tor_info_button = InfoButton(
            "About Tor",
            "<i>Tor</i> is an anonymizing network that helps defend against "
            "network surveillance and traffic analysis. With this checkbox "
            f"enabled, {APP_NAME} will route all traffic corresponding to this"
            " connection through the Tor network, concealing your geographical"
            " location from your storage provider and other parties (such as "
            "any persons with whom you might share folders).<p>"
            "Using this option requires that Tor already be installed and "
            "running on your computer and may be slower or less reliable than "
            "your normal internet connection.<p>"
            "For more information or to download Tor, please visit "
            "<a href=https://torproject.org>https://torproject.org</a>",
            self,
        )
        self.tor_info_button_effect = QGraphicsOpacityEffect()
        self.tor_info_button.setGraphicsEffect(self.tor_info_button_effect)
        self.tor_info_button.setAutoFillBackground(True)

        self.tor_info_button_animation_in = QPropertyAnimation(
            self.tor_info_button_effect, b"opacity"
        )
        self.tor_info_button_animation_in.setDuration(500)
        self.tor_info_button_animation_in.setStartValue(0)
        self.tor_info_button_animation_in.setEndValue(1)

        self.tor_info_button_animation_out = QPropertyAnimation(
            self.tor_info_button_effect, b"opacity"
        )
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
        tor_layout.addItem(HSpacer(), 1, 1)
        tor_layout.addWidget(self.tor_checkbox, 1, 2, Qt.AlignCenter)
        tor_layout.addWidget(self.tor_info_button, 1, 3, Qt.AlignLeft)
        tor_layout.addItem(HSpacer(), 1, 4)

        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color: red")
        self.error_label.setAlignment(Qt.AlignCenter)

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 1, 1)
        layout.addLayout(label_layout, 2, 1)
        layout.addWidget(self.lineedit, 3, 1)
        layout.addLayout(tor_layout, 4, 1)
        layout.addWidget(self.error_label, 5, 1)
        layout.addItem(VSpacer(), 6, 1)

        self.tor_checkbox.toggled.connect(self.toggle_tor_status)

        self.maybe_enable_tor_checkbox()

    @inlineCallbacks
    def maybe_enable_tor_checkbox(self) -> TwistedDeferred[None]:
        tor = yield get_tor(reactor)
        try:
            tor_checkbox_enabled = self.tor_checkbox.isEnabled()
        except RuntimeError:
            # In tests, this checkbox can get destroyed before the
            # get_tor Deferred returns, raising "builtins.RuntimeError:
            # wrapped C/C++ object of type QCheckBox has been deleted"
            logging.warning(
                "Wrapped object %s deleted before its methods could be called",
                self.tor_checkbox,
            )
            return
        if tor and not tor_checkbox_enabled:
            self.tor_checkbox.setEnabled(True)
            self.tor_checkbox_animation_in.start()
            self.tor_info_button_animation_in.start()
        elif not tor and tor_checkbox_enabled:
            self.tor_checkbox.setEnabled(False)
            self.tor_checkbox_animation_out.start()
            self.tor_info_button_animation_out.start()

    def toggle_tor_status(self, state: int) -> None:
        if state:
            msgbox = QMessageBox(self)
            msgbox.setIcon(QMessageBox.Warning)
            title = "Enable Tor?"
            text = (
                "Tor support in {} is currently <i>experimental</i> and may "
                "contain serious bugs that could jeopardize your anonymity.<p>"
                "Are you sure you wish to enable Tor for this connection?<br>".format(
                    APP_NAME
                )
            )
            if sys.platform == "darwin":
                msgbox.setText(title)
                msgbox.setInformativeText(text)
            else:
                msgbox.setWindowTitle(title)
                msgbox.setText(text)
            checkbox = QCheckBox(
                "I understand and accept the risks. Enable Tor."
            )
            msgbox.setCheckBox(checkbox)
            msgbox.setWindowModality(Qt.ApplicationModal)
            msgbox.exec_()
            if not checkbox.isChecked():
                self.tor_checkbox.setChecked(False)
                return
            self.lineedit.status_action.setIcon(self.lineedit.tor_icon)
            self.lineedit.status_action.setToolTip(
                "Tor: Enabled\n\n"
                "This connection will be routed through the Tor network."
            )
            # self.lineedit.setStyleSheet(
            #    "border-width: 1px;"
            #    "border-style: solid;"
            #    "border-color: {0};"
            #    "border-radius: 2px;"
            #    "padding: 2px;"
            #    "color: {0};".format(TOR_DARK_PURPLE))
        else:
            self.lineedit.status_action.setIcon(self.lineedit.blank_icon)
            self.lineedit.status_action.setToolTip("")
            # self.lineedit.setStyleSheet("")

    def get_code(self) -> str:
        return self.lineedit.text().lower()

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)

    def clear_error(self) -> None:
        self.error_label.setText("")


def show_failure(failure: Failure, parent: Optional[QWidget] = None) -> None:
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
            "some other problem with your connection. Please try again later."
        )
    elif failure.type == WelcomeError:
        msg.setWindowTitle("Invite refused")
        msg.setText(
            "The server negotiating your invitation is refusing to process "
            "any invitations."
        )
        msg.setInformativeText(
            "This may indicate that your version of {} is out-of-date, in "
            "which case you should upgrade to the latest version and try "
            "again.".format(APP_NAME)
        )
        msg.setIcon(QMessageBox.Critical)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setEscapeButton(QMessageBox.Ok)
    elif failure.type == WrongPasswordError:
        msg.setWindowTitle("Invite confirmation failed")
        msg.setText("Invite confirmation failed")
        msg.setInformativeText(
            "Either your recipient mistyped the invite code or a potential "
            "attacker tried to guess the code and failed.\n\nTo try again, "
            "you will need a new invite code."
        )
    elif failure.type == LonelyError:  # Raises only when closing(?)
        return
    elif failure.type == UpgradeRequiredError:
        msg.setWindowTitle("Upgrade required")
        msg.setText("Your version of {} is out-of-date.".format(APP_NAME))
        msg.setInformativeText(
            "Please upgrade to the latest version and try again with a new "
            "invite code."
        )
        msg.setIcon(QMessageBox.Critical)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setEscapeButton(QMessageBox.Ok)
    elif failure.type == CancelledError:
        msg.setWindowTitle("Invite timed out")
        msg.setText("The invitation process has timed out.")
        msg.setInformativeText(
            "Your invite code may have expired. Please request a new invite "
            "code from the other party and try again."
        )
    else:
        msg.setWindowTitle(str(failure.type.__name__))
        msg.setText(str(failure.value))
    msg.exec_()
