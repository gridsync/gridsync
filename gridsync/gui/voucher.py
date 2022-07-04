# -*- coding: utf-8 -*-
from typing import Optional

from qtpy.QtCore import Qt
from qtpy.QtGui import QFontDatabase
from qtpy.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QWidget

from gridsync.gui.font import Font
from gridsync.voucher import generate_voucher, is_valid


class VoucherCodeDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # self.setMinimumWidth(400)

        self.label = QLabel("Enter voucher code:")
        self.label.setFont(Font(14))
        self.label.setStyleSheet("color: gray")

        self.lineedit = QLineEdit(self)
        # self.lineedit.setFont(Font(14))
        # font = Font(14)
        # font.setStyleHint(QFont.Monospace)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(14)
        self.lineedit.setFont(font)
        mask = ">NNNN-NNNN-NNNN-NNNN"
        self.lineedit.setInputMask(mask)
        self.lineedit.setFixedWidth(
            self.lineedit.fontMetrics().boundingRect(mask).width() + 10
        )
        margins = self.lineedit.textMargins()
        margins.setLeft(margins.left() + 4)  # XXX
        self.lineedit.setTextMargins(margins)

        self.error_message_label = QLabel()
        self.error_message_label.setAlignment(Qt.AlignCenter)
        self.error_message_label.setFont(Font(10))
        self.error_message_label.setStyleSheet("color: red")

        layout = QGridLayout(self)
        layout.addWidget(self.label, 1, 1)
        layout.addWidget(self.lineedit, 2, 1)
        layout.addWidget(self.error_message_label, 3, 1)

        self.lineedit.returnPressed.connect(self.on_return_pressed)
        self.lineedit.textEdited.connect(
            lambda _: self.error_message_label.setText("")
        )

    def on_return_pressed(self) -> None:
        text = self.lineedit.text().replace("-", "")
        if is_valid(text):
            self.accept()
        else:
            self.error_message_label.setText("Invalid code; please try again")

    @staticmethod
    def get_voucher(parent: Optional[QWidget] = None) -> tuple[str, int]:
        dialog = VoucherCodeDialog(parent)
        result = dialog.exec_()
        return (
            generate_voucher(dialog.lineedit.text().replace("-", "").encode()),
            result,
        )
