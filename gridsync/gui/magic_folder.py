# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Optional, cast

from qtpy.QtCore import QFileInfo, Qt, Signal
from qtpy.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
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

from gridsync import config_dir
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.invite import InviteCodeWidget
from gridsync.gui.pixmap import Pixmap
from gridsync.gui.qrcode import QRCode
from gridsync.gui.widgets import HSpacer, InfoButton, VSpacer


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
        return self._get_data(id_, slot=self._INVITE_WAIT_DEFERRED_SLOT)

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
        self.cancel_button = self.button(QDialogButtonBox.Cancel)
        self.cancel_button.setIcon(QIcon())
        self.back_button = self.button(QDialogButtonBox.Reset)
        self.back_button.setIcon(QIcon())
        self.back_button.setText("&Back")


class _MagicFolderInviteParticipantPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.folder_icon = QLabel(self)
        self.folder_icon.setPixmap(
            QFileIconProvider().icon(QFileInfo(config_dir)).pixmap(64, 64)
        )

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

        self.button_box = ButtonBox(self)
        self.button_box.removeButton(self.button_box.back_button)

        layout = QGridLayout(self)
        layout.addItem(VSpacer(), 1, 1)
        layout.addWidget(self.folder_icon, 2, 1)
        layout.addLayout(label_layout, 3, 1)
        layout.addWidget(self.lineedit, 4, 1)
        layout.addItem(VSpacer(), 5, 1)
        layout.addWidget(self.button_box, 6, 1)


class _MagicFolderInviteCodePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.qrcode_label = QLabel("")
        self.label = QLabel("Code")
        self.button_box = ButtonBox(self)

        layout = QGridLayout(self)
        layout.addWidget(self.qrcode_label)
        layout.addWidget(self.label)
        layout.addWidget(self.button_box)

    def set_code(self, code: str) -> None:
        self.qrcode_label.setPixmap(QPixmap(QRCode(code).scaled(256, 256)))
        self.label.setText(code)


class _MagicFolderInviteSuccessPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.label = QLabel("Success")

        layout = QGridLayout(self)
        layout.addWidget(self.label)


class MagicFolderInviteDialog(QDialog):
    participant_name_set = Signal(str)
    cancel_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(500, 300)

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

        self._participant_page.button_box.ok_button.clicked.connect(
            self._on_participant_name_set
        )
        self._code_page.button_box.cancel_button.clicked.connect(
            self._on_cancel_requested
        )

    def _on_participant_name_set(self) -> None:
        participant_name = self._participant_page.lineedit.text()
        self.participant_name_set.emit(participant_name)

    def _on_cancel_requested(self) -> None:
        self.cancel_requested.emit()
        self.close()

    def show_code(self, code: str) -> None:
        self._code_page.set_code(code)
        self._stack.setCurrentWidget(self._code_page)

    def show_success(self) -> None:
        self._stack.setCurrentWidget(self._success_page)


class _MagicFolderJoinCodePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.mail_open_icon = QLabel()
        self.mail_open_icon.setAlignment(Qt.AlignCenter)
        self.mail_open_icon.setPixmap(Pixmap("mail-envelope-open.png", 128))

        self.invite_code_widget = InviteCodeWidget(self)

        self.button_box = ButtonBox(self)
        self.button_box.removeButton(self.button_box.back_button)

        layout = QGridLayout(self)
        layout.addWidget(self.mail_open_icon)
        layout.addWidget(self.invite_code_widget)
        layout.addWidget(HLine(self))
        layout.addWidget(self.button_box)


class _MagicFolderJoinPathPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.label = QLabel("Code")
        self.folder_name_lineedit = QLineEdit("", self)
        self.local_path_lineedit = QLineEdit("", self)
        self.browse_button = QPushButton("Browse...", self)

        self.button_box = ButtonBox(self)
        self.button_box.ok_button.setEnabled(False)

        layout = QGridLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.folder_name_lineedit)
        layout.addWidget(self.local_path_lineedit)
        layout.addWidget(self.browse_button)
        layout.addWidget(HLine(self))
        layout.addWidget(self.button_box)

        self.folder_name_lineedit.textChanged.connect(
            self._maybe_enable_ok_button
        )
        self.browse_button.clicked.connect(self._prompt_for_directory)

    def _maybe_enable_ok_button(self) -> None:
        if (
            self.folder_name_lineedit.text()
            and self.local_path_lineedit.text()
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


class _MagicFolderJoinSuccessPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.label = QLabel("Success")

        self.button = QPushButton("Close", self)

        layout = QGridLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.button)


class MagicFolderJoinDialog(QDialog):
    form_filled = Signal(str, str, str)  # folder_name, invite_code, local_path

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(500, 300)

        self._code_page = _MagicFolderJoinCodePage()
        self._path_page = _MagicFolderJoinPathPage()
        self._progress_page = _MagicFolderJoinProgressPage()
        self._success_page = _MagicFolderJoinSuccessPage()

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

        self._path_page.button_box.ok_button.clicked.connect(
            self._check_inputs
        )
        self._path_page.button_box.cancel_button.clicked.connect(self.close)
        self._path_page.button_box.back_button.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._code_page)
        )

    def _check_inputs(self) -> None:
        # XXX Validate
        folder_name = self._path_page.folder_name_lineedit.text()
        invite_code = self._code_page.invite_code_widget.get_code()
        local_path = self._path_page.local_path_lineedit.text()
        print(folder_name, invite_code, local_path)  # XXX
        self.form_filled.emit(folder_name, invite_code, local_path)

    def show_path(self) -> None:
        self._stack.setCurrentWidget(self._path_page)

    def show_progress(self) -> None:
        self._stack.setCurrentWidget(self._progress_page)

    def show_success(self) -> None:
        self._stack.setCurrentWidget(self._success_page)


if __name__ == "__main__":
    from qtpy.QtWidgets import (  # pylint: disable=ungrouped-imports
        QApplication,
    )

    app = QApplication([])
    w = MagicFolderJoinDialog()
    w.show()
    # w.show_code("3-test-test")
    # w.show_success()
    app.exec_()
