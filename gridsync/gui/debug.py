# -*- coding: utf-8 -*-

from datetime import datetime
import os
import platform
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
)

from gridsync import (
    APP_NAME, __version__, pkgdir, config_dir, autostart_file_path)
from gridsync.msg import error
from gridsync.desktop import get_clipboard_modes, set_clipboard_text


if sys.platform == 'darwin':
    system = 'macOS {}'.format(platform.mac_ver()[0])
elif sys.platform == 'win32':
    system = 'Windows {}'.format(platform.win32_ver()[0])
elif sys.platform.startswith('linux'):
    name, version, _ = platform.dist()  # pylint: disable=deprecated-method
    system = 'Linux ({} {})'.format(name, version)
else:
    system = platform.system()

header = """Application:  {} {}
System:       {}
Python:       {}
Frozen:       {}
""".format(
    APP_NAME,
    __version__,
    system,
    platform.python_version(),
    getattr(sys, 'frozen', False)
)


class DebugExporter(QDialog):
    def __init__(self, core, parent=None):
        super().__init__(parent=None)
        self.core = core
        self.parent = parent
        self.content = ''
        self.filtered_content = ''

        self.setMinimumSize(800, 600)
        self.setWindowTitle("{} - Debug Information".format(APP_NAME))

        self.plaintextedit = QPlainTextEdit(self)
        self.plaintextedit.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.plaintextedit.setFont(font)
        self.plaintextedit.setStyleSheet(
            "QPlainTextEdit { background-color: black; color: lime }"
        )

        self.scrollbar = self.plaintextedit.verticalScrollBar()
        self.scrollbar.valueChanged.connect(self.maybe_enable_buttons)

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.load)

        self.checkbox = QCheckBox(
            "Conceal potentially-identifying information", self)
        self.checkbox.setCheckState(Qt.Checked)
        self.checkbox.stateChanged.connect(self.on_checkbox_state_changed)

        self.copy_button = QPushButton("Copy to clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setEnabled(False)

        self.export_button = QPushButton("Export to file...")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.export_to_file)
        self.export_button.setEnabled(False)

        button_layout = QGridLayout()
        button_layout.addWidget(self.checkbox, 1, 1)
        button_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        button_layout.addWidget(self.reload_button, 1, 3)
        button_layout.addWidget(self.copy_button, 1, 4)
        button_layout.addWidget(self.export_button, 1, 5)

        layout = QGridLayout(self)
        layout.addWidget(self.plaintextedit, 1, 1)
        layout.addLayout(button_layout, 2, 1)

    def maybe_enable_buttons(self, scrollbar_value):
        if scrollbar_value == self.scrollbar.maximum():
            self.copy_button.setEnabled(True)
            self.export_button.setEnabled(True)

    def on_checkbox_state_changed(self, state):
        scrollbar_position = self.scrollbar.value()
        if state == Qt.Checked:
            self.plaintextedit.setPlainText(self.filtered_content)  # XXX
        else:
            self.plaintextedit.setPlainText(self.content)
        # Needed on some platforms to maintain scroll step accuracy/consistency
        self.scrollbar.setValue(self.scrollbar.maximum())
        self.scrollbar.setValue(scrollbar_position)

    def filter_content(self):
        fmt = '<Filtered:{}>'
        filters = [
            (pkgdir, fmt.format('PkgDir')),
            (config_dir, fmt.format('ConfigDir')),
            (autostart_file_path, fmt.format('AutostartFilePath')),
        ]
        filtered = self.content
        for s, mask in filters:
            filtered = filtered.replace(s, mask)
        self.filtered_content = filtered

    def load(self):
        if self.core.gui.main_window.gateways:
            names = [g.name for g in self.core.gui.main_window.gateways]
            gateways = ', '.join(names)
        else:
            gateways = 'None'
        self.content = (
            header
            + "Tahoe-LAFS:   {}\n".format(self.core.tahoe_version)
            + "Gateway(s):   {}\n".format(gateways)
            + "Datetime:     {}\n\n\n".format(datetime.utcnow().isoformat())
            + '\n'.join(self.core.log_deque)
        )
        self.filter_content()
        self.on_checkbox_state_changed(self.checkbox.checkState())
        self.maybe_enable_buttons(self.scrollbar.value())

    def copy_to_clipboard(self):
        for mode in get_clipboard_modes():
            set_clipboard_text(self.plaintextedit.toPlainText(), mode)
        self.close()

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

    def resizeEvent(self, _):
        if self.content:
            self.maybe_enable_buttons(self.scrollbar.value())
