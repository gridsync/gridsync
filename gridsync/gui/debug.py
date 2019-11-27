# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import os
import platform
import sys
import time

from atomicwrites import atomic_write
from PyQt5.QtCore import pyqtSignal, QObject, QSize, Qt, QThread
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
from gridsync.filter import get_filters, apply_filters, get_mask


if sys.platform == "darwin":
    system = "macOS {}".format(platform.mac_ver()[0])
elif sys.platform == "win32":
    system = "Windows {}".format(platform.win32_ver()[0])
elif sys.platform.startswith("linux"):
    import distro  # pylint: disable=import-error

    name, version, _ = distro.linux_distribution()
    system = "Linux ({} {})".format(name, version)
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
    getattr(sys, "frozen", False),
)


warning_text = (
    "####################################################################\n"
    "#                                                                  #\n"
    "#  WARNING: The following logs may contain sensitive information!  #\n"
    "#  Please exercise appropriate caution and review them carefully   #\n"
    "#  before copying, exporting, or otherwise sharing with others!    #\n"
    "#                                                                  #\n"
    "####################################################################\n\n"
)


class LogLoader(QObject):

    done = pyqtSignal()

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.content = ""
        self.filtered_content = ""

    def load(self):
        start_time = time.time()
        self.content = (
            header
            + "Tahoe-LAFS:   {}\n".format(self.core.tahoe_version)
            + "Datetime:     {}\n\n\n".format(datetime.utcnow().isoformat())
            + warning_text
            + "\n----- Beginning of {} debug log -----\n".format(APP_NAME)
            + "\n".join(self.core.log_deque)
            + "\n----- End of {} debug log -----\n".format(APP_NAME)
        )
        filters = get_filters(self.core)
        self.filtered_content = apply_filters(self.content, filters)
        for i, gateway in enumerate(self.core.gui.main_window.gateways):
            gateway_id = str(i + 1)
            gateway_mask = get_mask(gateway.name, "GatewayName", gateway_id)
            self.content = self.content + (
                "\n----- Beginning of Tahoe-LAFS log for {0} -----\n{1}"
                "\n----- End of Tahoe-LAFS log for {0} -----\n".format(
                    gateway.name, gateway.get_log()
                )
            )
            self.filtered_content = self.filtered_content + (
                "\n----- Beginning of Tahoe-LAFS log for {0} -----\n{1}"
                "\n----- End of Tahoe-LAFS log for {0} -----\n".format(
                    gateway_mask,
                    gateway.get_log(apply_filter=True, identifier=gateway_id),
                )
            )
        self.done.emit()
        logging.debug("Loaded logs in %f seconds", time.time() - start_time)


class DebugExporter(QDialog):
    def __init__(self, core, parent=None):
        super().__init__(parent=None)
        self.core = core
        self.parent = parent

        self.log_loader = LogLoader(self.core)
        self.log_loader_thread = QThread()
        self.log_loader.moveToThread(self.log_loader_thread)
        self.log_loader.done.connect(self.on_loaded)
        self.log_loader_thread.started.connect(self.log_loader.load)

        self.setMinimumSize(800, 600)
        self.setWindowTitle("{} - Debug Information".format(APP_NAME))

        self.plaintextedit = QPlainTextEdit(self)
        self.plaintextedit.setPlainText("Loading logs; please wait...")
        self.plaintextedit.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        self.plaintextedit.setFont(font)
        self.plaintextedit.setStyleSheet(
            "QPlainTextEdit { background-color: black; color: lime }"
        )

        self.scrollbar = self.plaintextedit.verticalScrollBar()

        self.reload_button = QPushButton("Reload")
        self.reload_button.clicked.connect(self.load)

        self.checkbox = QCheckBox(
            "Conceal potentially-identifying information", self
        )
        self.checkbox.setCheckState(Qt.Checked)
        self.checkbox.stateChanged.connect(self.on_checkbox_state_changed)

        self.filter_info_text = (
            "When enabled, {} will filter some information that could be used "
            "to identify a user or computer. This feature is not perfect, "
            "however, nor is it a substitute for manually checking logs for "
            "sensitive information before sharing.".format(APP_NAME)
        )
        self.filter_info_button = QPushButton()
        self.filter_info_button.setToolTip(self.filter_info_text)
        self.filter_info_button.setFlat(True)
        self.filter_info_button.setFocusPolicy(Qt.NoFocus)
        self.filter_info_button.setIcon(QIcon(resource("question")))
        self.filter_info_button.setIconSize(QSize(13, 13))
        if sys.platform == "darwin":
            self.filter_info_button.setFixedSize(16, 16)
        else:
            self.filter_info_button.setFixedSize(13, 13)
        self.filter_info_button.clicked.connect(
            self.on_filter_info_button_clicked
        )

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
            QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 2
        )
        bottom_layout.addLayout(buttons_layout, 1, 3)

        layout = QGridLayout(self)
        layout.addWidget(self.plaintextedit, 1, 1)
        layout.addLayout(bottom_layout, 2, 1)

    def on_checkbox_state_changed(self, state):
        scrollbar_position = self.scrollbar.value()
        if state == Qt.Checked:
            self.plaintextedit.setPlainText(self.log_loader.filtered_content)
        else:
            self.plaintextedit.setPlainText(self.log_loader.content)
        # Needed on some platforms to maintain scroll step accuracy/consistency
        self.scrollbar.setValue(self.scrollbar.maximum())
        self.scrollbar.setValue(scrollbar_position)

    def on_filter_info_button_clicked(self):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        if sys.platform == "darwin":
            msgbox.setText("About Log Filtering")
            msgbox.setInformativeText(self.filter_info_text)
        else:
            msgbox.setWindowTitle("About Log Filtering")
            msgbox.setText(self.filter_info_text)
        msgbox.show()

    def on_loaded(self):
        self.on_checkbox_state_changed(self.checkbox.checkState())
        self.log_loader_thread.quit()
        self.log_loader_thread.wait()

    def load(self):
        if self.log_loader_thread.isRunning():
            logging.warning("LogLoader thread is already running; returning")
            return
        self.log_loader_thread.start()

    def copy_to_clipboard(self):
        for mode in get_clipboard_modes():
            set_clipboard_text(self.plaintextedit.toPlainText(), mode)
        self.close()

    def export_to_file(self):
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Select a destination",
            os.path.join(
                os.path.expanduser("~"), APP_NAME + " Debug Information.txt"
            ),
        )
        if not dest:
            return
        try:
            with atomic_write(dest, mode="w", overwrite=True) as f:
                f.write(self.plaintextedit.toPlainText())
        except Exception as e:  # pylint: disable=broad-except
            logging.error("%s: %s", type(e).__name__, str(e))
            error(
                self, "Error exporting debug information", str(e),
            )
            return
        self.close()
