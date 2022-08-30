# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import collections
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Union

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication, QCheckBox, QMessageBox

# These Qt attributes must be set *before* initializing a QApplication...
if os.environ.get("QREXEC_REMOTE_DOMAIN") or os.environ.get(
    "QUBES_ENV_SOURCED"
):
    # On Qubes-OS, setting AA_EnableHighDpiScaling to 'True', *always* doubles
    # the window-size -- even on lower-resolution (1080p) displays -- but does
    # not do the same for font-sizes.
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    except AttributeError:  # Not available in Qt6
        pass
elif os.environ.get("DESKTOP_SESSION") == "mate":
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, False)
    except AttributeError:  # Not available in Qt6
        pass
else:
    try:
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    except AttributeError:  # Not available in Qt6
        pass
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
try:
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
except AttributeError:  # Not available in Qt6
    pass
try:
    QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
except AttributeError:  # Not available in Qt6
    pass

app = QApplication(sys.argv)

# qtreactor must be 'installed' after initializing QApplication but
# before running/importing any other Twisted code.
# See https://github.com/twisted/qt5reactor/blob/master/README.rst
from gridsync import qtreactor  # pylint: disable=ungrouped-imports

# Ignore mypy error 'Module has no attribute "install"'
qtreactor.install()  # type: ignore

# pylint: disable=wrong-import-order
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks

from gridsync import (
    APP_NAME,
    DEFAULT_AUTOSTART,
    cheatcode_used,
    config_dir,
    msg,
    resource,
    settings,
)
from gridsync.desktop import autostart_enable
from gridsync.gui import Gui
from gridsync.lock import FilesystemLock
from gridsync.magic_folder import MagicFolder
from gridsync.preferences import get_preference, set_preference
from gridsync.tahoe import Tahoe, get_nodedirs
from gridsync.tor import get_tor
from gridsync.types import TwistedDeferred

app.setWindowIcon(QIcon(resource(settings["application"]["tray_icon"])))


class Core:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.gateways: list = []
        self.tahoe_version: str = ""
        self.magic_folder_version: str = ""
        log_deque_maxlen = 100000  # XXX
        debug_settings = settings.get("debug")
        if debug_settings:
            log_maxlen = debug_settings.get("log_maxlen")
            if log_maxlen is not None:
                log_deque_maxlen = int(log_maxlen)
        self.log_deque: collections.deque = collections.deque(
            maxlen=log_deque_maxlen
        )

        if "log-privacy" in self.args:
            # Reflect that the user chose something with a command-line
            # argument.
            explicit = True
            private = self.args["log-privacy"]
        else:
            # Default to privacy mode out of an abundance of caution, but note
            # this is not an explicit user choice.
            explicit = False
            private = True

        privacy = LogPrivacy(logging.getLogger(), explicit=explicit, private=private)

        if "log-to-stdout" in self.args:
            mode: LogMode = StdoutMode(stdout)
        else:
            mode = MemoryMode(self.log_deque)

        initialize_logger(privacy, mode)

        # The `Gui` object must be initialized after initialize_logger,
        # otherwise log messages will be duplicated.
        self.gui = Gui(self)

    @inlineCallbacks
    def get_tahoe_version(self) -> TwistedDeferred[None]:
        tahoe = Tahoe()
        version = yield Deferred.fromCoroutine(tahoe.command(["--version"]))
        if version:
            self.tahoe_version = version.split("\n")[0]
            if self.tahoe_version.startswith("tahoe-lafs: "):
                self.tahoe_version = self.tahoe_version.lstrip("tahoe-lafs: ")

    @inlineCallbacks
    def get_magic_folder_version(self) -> TwistedDeferred[None]:
        magic_folder = MagicFolder(Tahoe())
        version = yield Deferred.fromCoroutine(magic_folder.version())
        if version:
            self.magic_folder_version = version.lstrip("Magic Folder version ")

    @staticmethod
    @inlineCallbacks
    def _start_gateway(gateway: Tahoe) -> TwistedDeferred[None]:
        try:
            yield Deferred.fromCoroutine(gateway.start())
        except Exception as e:  # pylint: disable=broad-except
            msg.critical(
                f"Error starting Tahoe-LAFS gateway for {gateway.name}",
                "A critical error occurred when attempting to start the "
                f'Tahoe-LAFS gateway for "{gateway.name}". {APP_NAME} will '
                'now exit.\n\nClick "Show Details..." for more information.',
                str(e),
            )

    @inlineCallbacks
    def _get_executable_versions(self) -> TwistedDeferred[None]:
        try:
            yield self.get_tahoe_version()
        except Exception as e:  # pylint: disable=broad-except
            msg.critical(
                "Error getting Tahoe-LAFS version",
                "{}: {}".format(type(e).__name__, str(e)),
            )
        try:
            yield self.get_magic_folder_version()
        except Exception as e:  # pylint: disable=broad-except
            msg.critical(
                "Error getting Magic-Folder version",
                "{}: {}".format(type(e).__name__, str(e)),
            )

    @inlineCallbacks
    def start_gateways(self) -> TwistedDeferred[None]:
        nodedirs = get_nodedirs(config_dir)
        if nodedirs:
            minimize_preference = get_preference("startup", "minimize")
            if not minimize_preference or minimize_preference == "false":
                self.gui.show_main_window()
            tor_available = yield get_tor(reactor)
            logging.debug("Starting Tahoe-LAFS gateway(s)...")
            for nodedir in nodedirs:
                gateway = Tahoe(nodedir)
                tcp = gateway.config_get("connections", "tcp")
                if tcp == "tor" and not tor_available:
                    logging.error("No running tor daemon found")
                    msg.error(
                        self.gui.main_window,
                        "Error Connecting To Tor Daemon",
                        'The "{}" connection is configured to use Tor, '
                        "however, no running tor daemon was found.\n\n"
                        "This connection will be disabled until you launch "
                        "Tor again.".format(gateway.name),
                    )
                self.gateways.append(gateway)
                self._start_gateway(gateway)
            self.gui.populate(self.gateways)
            cheatcode = settings.get("connection", {}).get("default")
            if cheatcode and not cheatcode_used(cheatcode):
                self.gui.show_welcome_dialog()
        else:
            self.gui.show_welcome_dialog()
            if DEFAULT_AUTOSTART:
                autostart_enable()
                self.gui.preferences_window.general_pane.load_preferences()
        yield self._get_executable_versions()

    @staticmethod
    def show_message() -> None:
        message_settings = settings.get("message")
        if not message_settings:
            return
        if get_preference("message", "suppress") == "true":
            return
        logging.debug("Showing custom message to user...")
        msgbox = QMessageBox()
        icon_type = message_settings.get("type")
        if icon_type:
            icon_type = icon_type.lower()
            if icon_type == "information":
                msgbox.setIcon(QMessageBox.Information)
            elif icon_type == "warning":
                msgbox.setIcon(QMessageBox.Warning)
            elif icon_type == "critical":
                msgbox.setIcon(QMessageBox.Critical)
        if sys.platform == "darwin":
            msgbox.setText(message_settings.get("title"))
            msgbox.setInformativeText(message_settings.get("text"))
        else:
            msgbox.setWindowTitle(message_settings.get("title"))
            msgbox.setText(message_settings.get("text"))
        checkbox = QCheckBox("Do not show this message again")
        checkbox.stateChanged.connect(
            lambda state: set_preference(
                "message", "suppress", ("true" if state else "false")
            )
        )
        msgbox.setCheckBox(checkbox)
        msgbox.exec_()
        logging.debug("Custom message closed; proceeding with start...")

    @inlineCallbacks
    def stop_gateways(self) -> TwistedDeferred[None]:
        yield DeferredList(
            [
                Deferred.fromCoroutine(gateway.stop())
                for gateway in self.gateways
            ]
        )

    def start(self) -> None:
        try:
            os.makedirs(config_dir)
        except OSError:
            pass

        # Acquire a filesystem lock to prevent multiple instances from running
        lock = FilesystemLock(
            os.path.join(config_dir, "{}.lock".format(APP_NAME))
        )
        lock.acquire()

        logging.debug("Core starting with args: %s", self.args)
        logging.debug("Loaded config.txt settings: %s", settings)

        self.show_message()

        self.gui.show_systray()

        reactor.callLater(0, self.start_gateways)  # type: ignore
        reactor.addSystemEventTrigger(  # type: ignore
            "before", "shutdown", self.stop_gateways
        )
        reactor.run()  # type: ignore
        lock.release()
