# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import platform
import sys
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

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
    QWidget,
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
    apply_eliot_filters,
    apply_filters,
    get_filters,
    get_mask,
)
from gridsync.gui.widgets import HSpacer
from gridsync.log import read_log
from gridsync.msg import error

if TYPE_CHECKING:
    from gridsync.core import Core


if sys.platform == "darwin":
    system = f"macOS {platform.mac_ver()[0]}"
elif sys.platform == "win32":
    system = f"Windows {platform.win32_ver()[0]}"
elif sys.platform.startswith("linux"):
    import distro  # pylint: disable=import-error

    name, version, _ = distro.linux_distribution()
    system = f"Linux ({name} {version})"
else:
    system = platform.system()


def _make_header(core: Core) -> str:
    return f"""\
Application:  {APP_NAME} {__version__}
System:       {system}
Python:       {platform.python_version()}
Frozen:       {getattr(sys, "frozen", False)}
Qt API:       {QT_API_VERSION} (Qt {QT_LIB_VERSION})
Tahoe-LAFS:   {core.tahoe_version}
Magic-Folder: {core.magic_folder_version}
Datetime:     {datetime.now(timezone.utc).isoformat()}


####################################################################
#                                                                  #
#  WARNING: The following logs may contain sensitive information!  #
#  Please exercise appropriate caution and review them carefully   #
#  before copying, saving, or otherwise sharing with others!       #
#                                                                  #
####################################################################


"""


def _format_log(log_name: str, content: str) -> str:
    if content and not content.endswith("\n"):
        content += "\n"
    return (
        f"-------------------- Beginning of {log_name} --------------------\n"
        f"{content}"
        f"-------------------- End of {log_name} --------------------\n\n"
    )


class LogLoader(QObject):
    done = Signal()

    def __init__(self, core: Core) -> None:
        super().__init__()
        self.core = core
        self.content = ""
        self.filtered_content = ""

    def load(self) -> None:
        start_time = time.time()
        self.content = _make_header(self.core) + _format_log(
            f"{APP_NAME} log", read_log()
        )
        filters = get_filters(self.core)
        self.filtered_content = apply_filters(self.content, filters)
        for i, gateway in enumerate(self.core.gui.main_window.gateways):
            gateway_id = str(i + 1)
            gateway_mask = get_mask(gateway.name, "GatewayName", gateway_id)

            tahoe_stdout = gateway.get_log("stdout")
            if tahoe_stdout:
                self.content += _format_log(
                    f"{gateway.name} Tahoe-LAFS stdout log", tahoe_stdout
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Tahoe-LAFS stdout log",
                    apply_filters(tahoe_stdout, filters),
                )
            tahoe_stderr = gateway.get_log("stderr")
            if tahoe_stderr:
                self.content += _format_log(
                    f"{gateway.name} Tahoe-LAFS stderr log", tahoe_stderr
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Tahoe-LAFS stderr log",
                    apply_filters(tahoe_stderr, filters),
                )
            tahoe_eliot = gateway.get_log("eliot")
            if tahoe_eliot:
                self.content += _format_log(
                    f"{gateway.name} Tahoe-LAFS eliot log", tahoe_eliot
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Tahoe-LAFS eliot log",
                    apply_eliot_filters(tahoe_eliot, gateway_id),
                )
            magic_folder_stdout = gateway.magic_folder.get_log("stdout")
            if magic_folder_stdout:
                self.content += _format_log(
                    f"{gateway.name} Magic-Folder stdout log",
                    magic_folder_stdout,
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Magic-Folder stdout log",
                    apply_filters(magic_folder_stdout, filters),
                )
            magic_folder_stderr = gateway.magic_folder.get_log("stderr")
            if magic_folder_stderr:
                self.content += _format_log(
                    f"{gateway.name} Magic-Folder stderr log",
                    magic_folder_stderr,
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Magic-Folder stderr log",
                    apply_filters(magic_folder_stderr, filters),
                )
            magic_folder_eliot = gateway.magic_folder.get_log("eliot")
            if magic_folder_eliot:
                self.content += _format_log(
                    f"{gateway.name} Magic-Folder eliot log",
                    magic_folder_eliot,
                )
                self.filtered_content += _format_log(
                    f"{gateway_mask} Magic-Folder eliot log",
                    apply_eliot_filters(magic_folder_eliot, gateway_id),
                )
        self.done.emit()
        logging.debug("Loaded logs in %f seconds", time.time() - start_time)


class DebugExporter(QDialog):
    def __init__(self, core: Core, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.core = core

        self.log_loader = LogLoader(self.core)
        self.log_loader_thread = QThread()
        self.log_loader.moveToThread(self.log_loader_thread)
        self.log_loader.done.connect(self.on_loaded)
        self.log_loader_thread.started.connect(self.log_loader.load)

        self.setMinimumSize(800, 600)
        self.setWindowTitle(f"{APP_NAME} - Debug Information")

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
            f"When enabled, {APP_NAME} will filter some information that "
            "could be used to identify a user or computer. This feature is "
            "not perfect, however, nor is it a substitute for manually "
            "checking logs for sensitive information before sharing."
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

    def on_checkbox_state_changed(self, state: int) -> None:
        scrollbar_position = self.scrollbar.value()
        if state == Qt.Checked:
            self.plaintextedit.setPlainText(self.log_loader.filtered_content)
        else:
            self.plaintextedit.setPlainText(self.log_loader.content)
        # Needed on some platforms to maintain scroll step accuracy/consistency
        self.scrollbar.setValue(self.scrollbar.maximum())
        self.scrollbar.setValue(scrollbar_position)

    def on_filter_info_button_clicked(self) -> None:
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        if sys.platform == "darwin":
            msgbox.setText("About Log Filtering")
            msgbox.setInformativeText(self.filter_info_text)
        else:
            msgbox.setWindowTitle("About Log Filtering")
            msgbox.setText(self.filter_info_text)
        msgbox.show()

    def on_loaded(self) -> None:
        self.on_checkbox_state_changed(self.checkbox.checkState())
        self.log_loader_thread.quit()
        self.log_loader_thread.wait()

    def load(self) -> None:
        if self.log_loader_thread.isRunning():
            logging.warning("LogLoader thread is already running; returning")
            return
        self.log_loader_thread.start()

    def copy_to_clipboard(self) -> None:
        for mode in get_clipboard_modes():
            set_clipboard_text(self.plaintextedit.toPlainText(), mode)
        self.close()

    def export_to_file(self) -> None:
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
