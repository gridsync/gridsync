# -*- coding: utf-8 -*-
from __future__ import annotations

from qtpy.QtCore import QFileInfo, Signal
from qtpy.QtGui import QPixmap
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
from gridsync.gui.qrcode import QRCode


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

        layout = QGridLayout(self)
        layout.addWidget(self.qrcode_label)
        layout.addWidget(self.label)

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

    def _on_participant_name_set(self) -> None:
        participant_name = self._participant_page.lineedit.text()
        self.participant_name_set.emit(participant_name)

    def show_code(self, code: str) -> None:
        self._code_page.set_code(code)
        self._stack.setCurrentWidget(self._code_page)

    def show_success(self) -> None:
        self._stack.setCurrentWidget(self._success_page)


if __name__ == "__main__":
    from qtpy.QtWidgets import (  # pylint: disable=ungrouped-imports
        QApplication,
    )

    app = QApplication([])
    w = MagicFolderInviteDialog()
    w.show()
    # w.show_code("3-test-test")
    # w.show_success()
    app.exec_()
