# -*- coding: utf-8 -*-

import os

from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
)

from gridsync import APP_NAME
from gridsync.msg import error
from gridsync.desktop import get_clipboard_modes, set_clipboard_text


class DebugExporter(QDialog):
    def __init__(self, core, parent=None):
        super().__init__(parent=None)
        self.core = core
        self.parent = parent

        self.setMinimumSize(800, 600)
        self.setWindowTitle("{} - Export Debug Information".format(APP_NAME))

        self.plaintextedit = QPlainTextEdit(self)
        self.plaintextedit.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.plaintextedit.setFont(font)

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.load)

        self.copy_button = QPushButton("Copy to clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        self.export_button = QPushButton("Export to file")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.export_to_file)

        button_layout = QGridLayout()
        button_layout.addWidget(self.reload_button, 1, 1)
        button_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        button_layout.addWidget(self.copy_button, 1, 3)
        button_layout.addWidget(self.export_button, 1, 4)

        layout = QGridLayout(self)
        layout.addWidget(self.plaintextedit, 1, 1)
        layout.addLayout(button_layout, 2, 1)

    def load(self):
        self.plaintextedit.setPlainText(str(self.core.log_output.getvalue()))

    def copy_to_clipboard(self):
        for mode in get_clipboard_modes():
            set_clipboard_text(self.plaintextedit.toPlainText(), mode)

    def export_to_file(self):
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Select a destination",
            os.path.join(
                os.path.expanduser('~'),
                APP_NAME + ' Debug Information.txt'))
        if not dest:
            return
        try:
            with open(dest, 'w') as f:
                f.write(self.plaintextedit.toPlainText())
        except Exception as e:  # pylint: disable=broad-except
            error(
                self,
                "Error exporting debug information",
                str(e),
            )
            return
        self.close()
