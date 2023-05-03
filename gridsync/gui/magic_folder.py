# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional, cast

from qtpy.QtCore import QFileInfo, Qt, Signal
from qtpy.QtGui import (
    QCloseEvent,
    QIcon,
    QKeyEvent,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QWidget,
)
from twisted.internet.defer import Deferred

from gridsync import config_dir, resource
from gridsync.crypto import randstr
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.invite import (
    InviteCodeBox,
    InviteCodeWidget,
    InviteHeaderWidget,
)
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.qrcode import QRCode
from gridsync.gui.widgets import HSpacer, InfoButton, VSpacer
from gridsync.msg import question


class MagicFolderInvitesModel(QStandardItemModel):
    _INVITE_WAIT_DEFERRED_SLOT: int = 1
    _DIALOG_SLOT: int = 2

    def __init__(self) -> None:
        super().__init__(0, 2)

    def add_invite(self, id_: str, wormhole_code: str) -> None:
        self.appendRow(
            [
                QStandardItem(id_),
                QStandardItem(wormhole_code),
            ]
        )

    def get_wormhole_code(self, id_: str) -> Optional[str]:
        items = self.findItems(id_)
        if items:
            return self.item(items[0].row(), 1).text()
        return None

    def _set_data(self, id_: str, value: object, slot: int = 0) -> None:
        items = self.findItems(id_)
        if not items:
            return
        item = self.item(items[0].row(), 0)
        item.setData(value, role=Qt.UserRole + 1 + slot)

    def _get_data(self, id_: str, slot: int = 0) -> Optional[object]:
        items = self.findItems(id_)
        if not items:
            return None
        item = self.item(items[0].row(), 0)
        return item.data(Qt.UserRole + 1 + slot)

    def set_invite_wait_deferred(
        self, id_: str, d: Optional[Deferred]
    ) -> None:
        self._set_data(id_, d, slot=self._INVITE_WAIT_DEFERRED_SLOT)

    def get_invite_wait_deferred(self, id_: str) -> Optional[Deferred]:
        d = self._get_data(id_, slot=self._INVITE_WAIT_DEFERRED_SLOT)
        if isinstance(d, Deferred):
            return d
        return None

    def set_dialog(self, id_: str, dialog: MagicFolderInviteDialog) -> None:
        self._set_data(id_, dialog, slot=self._DIALOG_SLOT)

    def get_dialog(self, id_: str) -> Optional[MagicFolderInviteDialog]:
        dialog = self._get_data(id_, slot=self._DIALOG_SLOT)
        if dialog is None:
            return None
        return cast(MagicFolderInviteDialog, dialog)


class HLine(QFrame):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShadow(QFrame.Sunken)
        self.setFrameShape(QFrame.HLine)


class ButtonBox(QDialogButtonBox):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel
            | QDialogButtonBox.Reset,
            parent,
        )
        self.ok_button = self.button(QDialogButtonBox.Ok)
        self.ok_button.setIcon(QIcon())
        self.ok_button.setFocusPolicy(Qt.NoFocus)
        self.cancel_button = self.button(QDialogButtonBox.Cancel)
        self.cancel_button.setIcon(QIcon())
        self.cancel_button.setFocusPolicy(Qt.NoFocus)
        self.back_button = self.button(QDialogButtonBox.Reset)
        self.back_button.setIcon(QIcon())
        self.back_button.setFocusPolicy(Qt.NoFocus)
        self.back_button.setText("&Back")


class _MagicFolderInviteParticipantPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.header = InviteHeaderWidget(self)
        self.header.set_icon(QFileIconProvider().icon(QFileInfo(config_dir)))

        self.label = QLabel("Enter device name:", self)
        self.label.setFont(Font(14))
        p = self.palette()
        grey = BlendedColor(p.windowText().color(), p.window().color()).name()
        self.label.setStyleSheet(f"color: {grey}")
        self.label.setAlignment(Qt.AlignCenter)

        self.device_info_button = InfoButton(
            "About Device Names",
            "A label for the device being invited to the folder.<p>This name "
            "will be visible to all other participants in the folder.",
            self,
        )

        label_layout = QGridLayout()
        label_layout.setHorizontalSpacing(6)
        label_layout.addItem(HSpacer(), 1, 1)
        label_layout.addWidget(self.label, 1, 2, Qt.AlignCenter)
        label_layout.addWidget(self.device_info_button, 1, 3, Qt.AlignLeft)
        label_layout.addItem(HSpacer(), 1, 5)

        self.lineedit = QLineEdit(self)
        self.lineedit.setFont(Font(16))
        self.lineedit.setAlignment(Qt.AlignCenter)

        self.checkbox = QCheckBox("This device may only read updates")
        self.checkbox.setStyleSheet(f"QCheckBox {{ color: {grey} }}")

        self.button_box = ButtonBox(self)
        self.button_box.removeButton(self.button_box.back_button)
        self.button_box.ok_button.setText("Create Invite...")
        self.button_box.ok_button.setEnabled(False)

        layout = QGridLayout(self)
        # layout.addItem(VSpacer(), 0, 0)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.header, 2, 2, 1, 3)
        layout.addItem(VSpacer(), 3, 1)
        layout.addLayout(label_layout, 4, 2, 1, 3)
        layout.addWidget(self.lineedit, 5, 2, 1, 3)
        layout.addWidget(self.checkbox, 6, 2, 1, 3, Qt.AlignCenter)
        layout.addItem(VSpacer(), 7, 1)
        layout.addWidget(HLine(self), 8, 1, 1, 5)
        layout.addWidget(self.button_box, 9, 1, 1, 5)

        self.lineedit.textChanged.connect(self._on_text_changed)
        # Call last, as this depends on the initialization of self.button_box
        self.lineedit.setText(f"Device-{randstr(6)}")

    def _on_text_changed(self) -> None:
        if self.lineedit.text():
            self.button_box.ok_button.setEnabled(True)
        else:
            self.button_box.ok_button.setEnabled(False)


class _MagicFolderInviteCodePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.qrcode_label = QLabel("")
        self.qrcode_label.setAlignment(Qt.AlignCenter)

        self.code_box = InviteCodeBox(self)

        self.text_label = QLabel("", self)
        self.text_label.setAlignment(Qt.AlignCenter)
        p = self.palette()
        grey = BlendedColor(p.windowText().color(), p.window().color()).name()
        self.text_label.setStyleSheet(f"color: {grey}")
        self.text_label.setWordWrap(True)

        self.cancel_button = QPushButton("Close and cancel", self)

        layout = QGridLayout(self)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addItem(VSpacer(), 3, 1)
        layout.addWidget(self.qrcode_label, 4, 2, 1, 3)
        layout.addWidget(self.code_box, 5, 2, 1, 3)
        layout.addWidget(self.text_label, 6, 2, 1, 3)
        layout.addItem(VSpacer(), 7, 1)
        layout.addWidget(HLine(self), 8, 1, 1, 5)
        layout.addWidget(self.cancel_button, 9, 3, 1, 1)

        self.code_box.copy_button.clicked.connect(
            lambda: self.text_label.setText(
                f"Copied '{self.code_box.get_code()}' to clipboard!\n\n\n"
            )
        )

    def set_code(self, code: str) -> None:
        self.qrcode_label.setPixmap(QPixmap(QRCode(code).scaled(128, 128)))
        self.code_box.show_code(code)


class _MagicFolderInviteSuccessPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.title_label = QLabel("Invite complete!", self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(Font(16))

        self.checkmark = QLabel(self)
        self.checkmark.setPixmap(Pixmap(resource("green_checkmark.png"), 96))
        self.checkmark.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel("", self)
        self.text_label.setAlignment(Qt.AlignCenter)
        p = self.palette()
        grey = BlendedColor(p.windowText().color(), p.window().color()).name()
        self.text_label.setStyleSheet(f"color: {grey}")
        self.text_label.setWordWrap(True)

        self.close_button = QPushButton("Close", self)

        layout = QGridLayout(self)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addItem(VSpacer(), 2, 1)
        layout.addWidget(self.title_label, 3, 2, 1, 3)
        layout.addItem(VSpacer(), 4, 1)
        layout.addWidget(self.checkmark, 5, 2, 1, 3)
        layout.addItem(VSpacer(), 6, 1)
        layout.addWidget(self.text_label, 7, 2, 1, 3)
        layout.addItem(VSpacer(), 8, 1)
        layout.addWidget(HLine(self), 9, 1, 1, 5)
        layout.addWidget(self.close_button, 10, 3, 1, 1)

    def set_text(self, text: str) -> None:
        self.text_label.setText(text)


class MagicFolderInviteDialog(QDialog):
    form_filled = Signal(str, str)  # participant_name, mode
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._folder_name: str = ""
        self._participant_name: str = ""

        self.setMinimumSize(660, 440)
        self.setWindowTitle("Create Folder Invite")

        self._participant_page = _MagicFolderInviteParticipantPage()
        self._code_page = _MagicFolderInviteCodePage()
        self._success_page = _MagicFolderInviteSuccessPage()

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._participant_page)
        self._stack.addWidget(self._code_page)
        self._stack.addWidget(self._success_page)

        layout = QGridLayout(self)
        layout.addWidget(self._stack)

        self._stack.setCurrentWidget(self._participant_page)

        self._participant_page.button_box.cancel_button.clicked.connect(
            self.close
        )
        self._participant_page.button_box.ok_button.clicked.connect(
            self._on_ok_button_clicked
        )
        self._participant_page.lineedit.returnPressed.connect(
            self._on_return_pressed
        )

        self._code_page.cancel_button.clicked.connect(self.close)

        self._success_page.close_button.clicked.connect(self.close)

    def _on_ok_button_clicked(self) -> None:
        self._participant_name = self._participant_page.lineedit.text()
        if self._participant_page.checkbox.isChecked():
            mode = "read-only"
            abilities = "read but not modify"
        else:
            mode = "read-write"
            abilities = "read and modify"
        self._code_page.text_label.setText(
            f"Enter this code on another device to allow it to {abilities} "
            f'the contents of the "{self._folder_name}" folder.\n'
            "This code can only be used once."
        )
        self.form_filled.emit(self._participant_name, mode)

    def _on_return_pressed(self) -> None:
        if self._participant_page.lineedit.text():
            self._on_ok_button_clicked()  # XXX

    def _on_cancel_requested(self) -> None:
        self.cancel_requested.emit()
        self.close()

    def set_folder_name(self, folder_name: str) -> None:
        self._participant_page.header.set_text(folder_name)
        self.setWindowTitle(f"Create Folder Invite: {folder_name}")
        self._folder_name = folder_name

    def show_code(self, code: str) -> None:
        self._code_page.set_code(code)
        self._stack.setCurrentWidget(self._code_page)

    def show_success(self) -> None:
        self._success_page.set_text(
            f"You have successfully invited {self._participant_name} to the "
            f'"{self._folder_name}" folder!'
        )
        self._stack.setCurrentWidget(self._success_page)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._stack.currentWidget() == self._code_page:
            if question(
                self,
                "Cancel invite?",
                f"Are you sure you wish to cancel the invite to "
                f'"{self._folder_name}?"\n\nThe invite code '
                f"{self._code_page.code_box.get_code()} will no longer be "
                "valid.",
            ):
                self.cancel_requested.emit()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()


class _MagicFolderJoinCodePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.mail_open_icon = QLabel()
        self.mail_open_icon.setAlignment(Qt.AlignCenter)
        self.mail_open_icon.setPixmap(Pixmap("mail-envelope-open.png", 128))

        self.invite_code_widget = InviteCodeWidget(self)

        self.button_box = ButtonBox(self)
        self.button_box.removeButton(self.button_box.back_button)
        self.button_box.ok_button.setEnabled(False)

        layout = QGridLayout(self)
        # layout.addItem(VSpacer(), 0, 0)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.mail_open_icon, 2, 2, 1, 3)
        layout.addItem(VSpacer(), 3, 1)
        layout.addWidget(self.invite_code_widget, 6, 2, 1, 3, Qt.AlignCenter)
        layout.addItem(VSpacer(), 7, 1)
        layout.addWidget(HLine(self), 8, 1, 1, 5)
        layout.addWidget(self.button_box, 9, 1, 1, 5)

        self.invite_code_widget.code_validated.connect(
            lambda _: self.button_box.ok_button.setEnabled(True)
        )
        self.invite_code_widget.code_invalidated.connect(
            lambda _: self.button_box.ok_button.setEnabled(False)
        )


class _MagicFolderJoinPathPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.mail_open_icon = QLabel(self)
        self.mail_open_icon.setAlignment(Qt.AlignCenter)
        self.mail_open_icon.setPixmap(Pixmap("mail-envelope-open.png", 128))

        self.folder_name_label = QLabel("Folder name:", self)
        self.folder_name_label.setFont(Font(14))
        p = self.palette()
        grey = BlendedColor(p.windowText().color(), p.window().color()).name()
        self.folder_name_label.setStyleSheet(f"color: {grey}")

        self.folder_name_lineedit = QLineEdit("", self)
        self.folder_name_lineedit.setFont(Font(14))

        self.location_label = QLabel("Location:", self)
        self.location_label.setFont(Font(14))
        self.location_label.setStyleSheet(f"color: {grey}")

        self.local_path_lineedit = QLineEdit(str(Path().home()), self)
        self.local_path_lineedit.setFont(Font(14))

        self.browse_button = QPushButton("Browse...", self)

        self.text_label = QLabel(
            "Select a folder name and location.\n"
            "The new folder will be created inside the location you choose.",
            self,
        )
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setStyleSheet(f"color: {grey}")
        self.text_label.setWordWrap(True)

        folder_layout = QGridLayout()
        folder_layout.setHorizontalSpacing(6)
        folder_layout.addWidget(self.folder_name_label, 1, 2)
        folder_layout.addWidget(self.folder_name_lineedit, 1, 4, Qt.AlignLeft)

        folder_layout.addWidget(self.location_label, 2, 2)
        folder_layout.addWidget(self.local_path_lineedit, 2, 4, Qt.AlignLeft)
        folder_layout.addWidget(self.browse_button, 2, 5, Qt.AlignLeft)

        self.button_box = ButtonBox(self)
        self.button_box.ok_button.setEnabled(False)

        layout = QGridLayout(self)
        layout.addItem(HSpacer(), 1, 1)
        layout.addItem(HSpacer(), 1, 2)
        layout.addItem(HSpacer(), 1, 3)
        layout.addItem(HSpacer(), 1, 4)
        layout.addItem(HSpacer(), 1, 5)
        layout.addWidget(self.mail_open_icon, 2, 2, 1, 3)
        layout.addItem(VSpacer(), 3, 1)
        layout.addLayout(folder_layout, 4, 2, 1, 3)
        layout.addItem(VSpacer(), 5, 1)
        layout.addWidget(self.text_label, 6, 2, 1, 3)
        layout.addItem(VSpacer(), 7, 1)
        layout.addWidget(HLine(self), 8, 1, 1, 5)
        layout.addWidget(self.button_box, 9, 1, 1, 5)

        self.folder_name_lineedit.textChanged.connect(
            self._maybe_enable_ok_button
        )
        self.local_path_lineedit.textChanged.connect(
            self._maybe_enable_ok_button
        )
        self.browse_button.clicked.connect(self._prompt_for_directory)

    def get_folder_name(self) -> str:
        return self.folder_name_lineedit.text()

    def get_local_path(self) -> str:
        return self.local_path_lineedit.text()

    def _maybe_enable_ok_button(self) -> None:
        local_path = self.get_local_path()
        if (
            self.folder_name_lineedit.text()
            and local_path
            and Path(local_path).exists()
        ):
            self.button_box.ok_button.setEnabled(True)

    def _prompt_for_directory(self) -> None:
        caption = "Choose a save location"
        folder_name = self.folder_name_lineedit.text()
        if folder_name:
            caption += f" for {folder_name}"
        directory = QFileDialog.getExistingDirectory(
            self, caption, str(Path.home().resolve())
        )
        if directory:
            self.local_path_lineedit.setText(str(Path(directory).resolve()))
            self._maybe_enable_ok_button()


class _MagicFolderJoinProgressPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.label = QLabel("Progress")

        layout = QGridLayout(self)
        layout.addWidget(self.label)


class MagicFolderJoinDialog(QDialog):
    form_filled = Signal(str, str, str)  # folder_name, invite_code, local_path

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(660, 440)
        self.setWindowTitle("Join Folder")

        self._code_page = _MagicFolderJoinCodePage()
        self._path_page = _MagicFolderJoinPathPage()
        self._progress_page = _MagicFolderJoinProgressPage()
        self._success_page = _MagicFolderInviteSuccessPage()

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._code_page)
        self._stack.addWidget(self._path_page)
        self._stack.addWidget(self._progress_page)
        self._stack.addWidget(self._success_page)
        self._stack.setCurrentWidget(self._code_page)

        layout = QGridLayout(self)
        layout.addWidget(self._stack)

        self._code_page.button_box.ok_button.clicked.connect(self.show_path)
        self._code_page.button_box.cancel_button.clicked.connect(self.close)
        self._code_page.invite_code_widget.code_entered.connect(
            lambda _: self.show_path()
        )

        self._path_page.button_box.ok_button.clicked.connect(
            self._check_inputs
        )
        self._path_page.button_box.cancel_button.clicked.connect(self.close)
        self._path_page.button_box.back_button.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._code_page)
        )

        self._success_page.close_button.clicked.connect(self.close)

    def _check_inputs(self) -> None:
        folder_name = self._path_page.folder_name_lineedit.text()
        invite_code = self._code_page.invite_code_widget.get_code()
        local_path = self._path_page.local_path_lineedit.text()
        local_path = str(Path(local_path, folder_name))
        self._success_page.set_text(
            f'You have successfully joined the "{folder_name}" folder!'
        )
        self.form_filled.emit(folder_name, invite_code, local_path)
        # Prevent changes after wormhole has been opened
        self._path_page.button_box.ok_button.setEnabled(False)
        self._path_page.folder_name_lineedit.setEnabled(False)
        self._path_page.local_path_lineedit.setEnabled(False)
        self._path_page.browse_button.setEnabled(False)

    def show_path(self) -> None:
        self._stack.setCurrentWidget(self._path_page)

    def show_progress(self) -> None:
        self._stack.setCurrentWidget(self._progress_page)

    def show_success(self) -> None:
        self._stack.setCurrentWidget(self._success_page)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
