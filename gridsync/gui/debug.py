# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDialog, QGridLayout, QPlainTextEdit


class DebugExporter(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=None)
        self.parent = parent

        self.plaintextedit = QPlainTextEdit(self)
        self.plaintextedit.setReadOnly(True)

        layout = QGridLayout(self)
        layout.addWidget(self.plaintextedit)

    def load(self, core):
        self.plaintextedit.setPlainText(str(core.log_output.getvalue()))
