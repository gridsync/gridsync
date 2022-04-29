# -*- coding: utf-8 -*-

import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone

from atomicwrites import atomic_write
from qtpy.QtCore import QObject, QSize, Qt, QThread, Signal
from qtpy.QtGui import QFontDatabase, QIcon
from qtpy.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
)

from gridsync import (
    APP_NAME,
    QT_API_VERSION,
    QT_LIB_VERSION,
    __version__,
    resource,
)
from gridsync.desktop import get_clipboard_modes, set_clipboard_text
from gridsync.filter import (
    apply_filters,
    filter_eliot_logs,
    get_filters,
    get_mask,
    join_eliot_logs,
)
from gridsync.gui.widgets import HSpacer
from gridsync.msg import error

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
Qt API:       {} (Qt {})
""".format(
    APP_NAME,
    __version__,
    system,
    platform.python_version(),
    getattr(sys, "frozen", False),
    QT_API_VERSION,
    QT_LIB_VERSION,
)


warning_text = (
    "####################################################################\n"
    "#                                                                  #\n"
    "#  WARNING: The following logs may contain sensitive information!  #\n"
    "#  Please exercise appropriate caution and review them carefully   #\n"
    "#  before copying, saving, or otherwise sharing with others!       #\n"
    "#                                                                  #\n"
    "####################################################################\n\n"
)


def log_fmt(gateway_name: str, tahoe_log: str, magic_folder_log: str) -> str:
    return (
        f"\n------ Beginning of Tahoe-LAFS log for {gateway_name} ------\n"
        f"{tahoe_log}"
        f"\n------ End of Tahoe-LAFS log for {gateway_name} ------\n"
        f"\n------ Beginning of Magic-Folder log for {gateway_name} ------\n"
        f"{magic_folder_log}"
        f"\n------ End of Magic-Folder log for {gateway_name} ------\n"
    )


class LogLoader(QObject):

    done = Signal()

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
            + "Magic-Folder: {}\n".format(self.core.magic_folder_version)
            + "Datetime:     {}\n\n\n".format(
                datetime.now(timezone.utc).isoformat()
            )
            + warning_text
            + "\n----- Beginning of {} debug log -----\n".format(APP_NAME)
            + "\n".join(self.core.log_deque)
            + "\n----- End of {} debug log -----\n".format(APP_NAME)
        )
        filters = get_filters(self.core)
        self.filtered_content = apply_filters(self.content, filters)
        for i, gateway in enumerate(self.core.gui.main_window.gateways):
            gateway_id = str(i + 1)
            self.content = self.content + log_fmt(
                gateway.name,
                join_eliot_logs(gateway.get_streamed_log_messages()),
                join_eliot_logs(gateway.magic_folder.get_log_messages()),
            )
            self.filtered_content = self.filtered_content + log_fmt(
                get_mask(gateway.name, "GatewayName", gateway_id),
                join_eliot_logs(
                    filter_eliot_logs(
                        gateway.get_streamed_log_messages(), gateway_id
                    )
                ),
                join_eliot_logs(
                    filter_eliot_logs(
                        gateway.magic_folder.get_log_messages(), gateway_id
                    )
                ),
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

        self.export_button = QPushButton("Save to file...")
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
        bottom_layout.addItem(HSpacer(), 1, 2)
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
            error(self, "Error saving debug information", str(e))
            return
        self.close()
