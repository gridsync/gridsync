# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from qtpy.QtCore import QFileInfo, Signal
from qtpy.QtGui import QPixmap, QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QDialog,
    QFileIconProvider,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QWidget,
)

from gridsync import config_dir
from gridsync.gui.invite import InviteCodeLineEdit
from gridsync.gui.qrcode import QRCode


class MagicFolderInvitesModel(QStandardItemModel):
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


class _MagicFolderInviteParticipantPage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.folder_icon = QLabel(self)
        self.folder_icon.setPixmap(
            QFileIconProvider().icon(QFileInfo(config_dir)).pixmap(64, 64)
        )

        self.label = QLabel("Participant name:")

        self.lineedit = QLineEdit(self)

        self.button = QPushButton("Create Invite...")

        layout = QGridLayout(self)
        layout.addWidget(self.folder_icon)
        layout.addWidget(self.label)
        layout.addWidget(self.lineedit)
        layout.addWidget(self.button)


class _MagicFolderInviteCodePage(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.qrcode_label = QLabel("")
        self.label = QLabel("Code")

        self.button = QPushButton("Cancel")

        layout = QGridLayout(self)
        layout.addWidget(self.qrcode_label)
        layout.addWidget(self.label)
        layout.addWidget(self.button)

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

        self._participant_page.button.clicked.connect(
            self._on_participant_name_set
        )
        self._code_page.button.clicked.connect(self._on_cancel_requested)

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

        self.label = QLabel("Code")
        self.folder_name_lineedit = QLineEdit(self)
        self.invite_code_lineedit = InviteCodeLineEdit(self)
        self.local_path_lineedit = QLineEdit(self)
        self.button = QPushButton("Go")

        layout = QGridLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.folder_name_lineedit)
        layout.addWidget(self.invite_code_lineedit)
        layout.addWidget(self.local_path_lineedit)
        layout.addWidget(self.button)


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

        layout = QGridLayout(self)
        layout.addWidget(self.label)


class MagicFolderJoinDialog(QDialog):
    form_filled = Signal(str, str, str)  # folder_name, invite_code, local_path

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(500, 300)

        self._code_page = _MagicFolderJoinCodePage()
        self._progress_page = _MagicFolderJoinProgressPage()
        self._success_page = _MagicFolderJoinSuccessPage()

        self._stack = QStackedWidget(self)
        self._stack.addWidget(self._code_page)
        self._stack.addWidget(self._progress_page)
        self._stack.addWidget(self._success_page)
        self._stack.setCurrentWidget(self._code_page)

        layout = QGridLayout(self)
        layout.addWidget(self._stack)

        self._code_page.button.clicked.connect(self._on_button_clicked)

    def _on_button_clicked(self) -> None:
        folder_name = self._code_page.folder_name_lineedit.text()
        invite_code = self._code_page.invite_code_lineedit.text()
        local_path = self._code_page.local_path_lineedit.text()
        print(folder_name, invite_code, local_path)  # XXX
        self.form_filled.emit(folder_name, invite_code, local_path)

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
