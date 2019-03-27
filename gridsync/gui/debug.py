# -*- coding: utf-8 -*-

from datetime import datetime
import os
import platform
import sys

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFontDatabase, QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
)

from gridsync import APP_NAME, __version__, resource
from gridsync.msg import error
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.filter import get_filters, apply_filters


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

        self.filter_info_text = (
            'With this checkbox enabled, {} will attempt to remove or filter '
            'out certain types of known information (such as folder names) '
            'from exported logs that could potentially be used to identify a '
            'given user or computer.\n\nThis feature is not perfect, however, '
            'and it is still possible that logs may contain sensitive '
            'information. Accordingly, it is important to manually inspect '
            'the contents of logs to verify that they contain no sensitive '
            'information before sharing with others.'.format(APP_NAME)
        )
        self.filter_info_button = QPushButton()
        self.filter_info_button.setToolTip(self.filter_info_text)
        self.filter_info_button.setFlat(True)
        self.filter_info_button.setFocusPolicy(Qt.NoFocus)
        self.filter_info_button.setIcon(QIcon(resource('question')))
        self.filter_info_button.setIconSize(QSize(13, 13))
        if sys.platform == 'darwin':
            self.filter_info_button.setFixedSize(16, 16)
        else:
            self.filter_info_button.setFixedSize(13, 13)
        self.filter_info_button.clicked.connect(
            self.on_filter_info_button_clicked)

        self.copy_button = QPushButton("Copy to clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)

        self.export_button = QPushButton("Export to file...")
        self.export_button.setDefault(True)
        self.export_button.clicked.connect(self.export_to_file)

        checkbox_layout = QGridLayout()
        checkbox_layout.setHorizontalSpacing(0)
        checkbox_layout.addWidget(self.checkbox, 1, 1)
        checkbox_layout.addWidget(self.filter_info_button, 1, 2)

        buttons_layout = QGridLayout()
        buttons_layout.addWidget(self.reload_button, 1, 1)
        buttons_layout.addWidget(self.copy_button, 1, 2)
        buttons_layout.addWidget(self.export_button, 1, 3)

        bottom_layout = QGridLayout()
        bottom_layout.addLayout(checkbox_layout, 1, 1)
        bottom_layout.addItem(
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2)
        bottom_layout.addLayout(buttons_layout, 1, 3)

        layout = QGridLayout(self)
        layout.addWidget(self.plaintextedit, 1, 1)
        layout.addLayout(bottom_layout, 2, 1)

    def maybe_enable_buttons(self, scrollbar_value):
        if scrollbar_value == self.scrollbar.maximum():
            self.copy_button.setEnabled(True)
            self.export_button.setEnabled(True)
        else:
            self.copy_button.setEnabled(False)
            self.export_button.setEnabled(False)

    def on_checkbox_state_changed(self, state):
        scrollbar_position = self.scrollbar.value()
        if state == Qt.Checked:
            self.plaintextedit.setPlainText(self.filtered_content)  # XXX
        else:
            self.plaintextedit.setPlainText(self.content)
        # Needed on some platforms to maintain scroll step accuracy/consistency
        self.scrollbar.setValue(self.scrollbar.maximum())
        self.scrollbar.setValue(scrollbar_position)

    def on_filter_info_button_clicked(self):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        if sys.platform == 'darwin':
            msgbox.setText("About Log Filtering")
            msgbox.setInformativeText(self.filter_info_text)
        else:
            msgbox.setWindowTitle("About Log Filtering")
            msgbox.setText(self.filter_info_text)
        msgbox.show()

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
        filters = get_filters(self.core)
        self.filtered_content = apply_filters(self.content, filters)
        #self.filter_content()
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
        self.maybe_enable_buttons(self.scrollbar.value())
