# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import cast

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QApplication, QCheckBox, QMessageBox

# Global QApplication attributes must be set *before* instantiating
# a QApplication object.
# https://doc.qt.io/qt-6/qt.html#HighDpiScaleFactorRoundingPolicy-enum
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
app = QApplication(sys.argv)

# qtreactor must be 'installed' after initializing QApplication but
# before running/importing any other Twisted code.
# See https://github.com/twisted/qt5reactor/blob/master/README.rst
from gridsync import qtreactor  # pylint: disable=ungrouped-imports

# Ignore mypy error 'Module has no attribute "install"'
qtreactor.install()  # type: ignore

# pylint: disable=wrong-import-order
from twisted.internet import reactor as reactor_module
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks
from twisted.internet.interfaces import IReactorCore

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
from gridsync.errors import UpgradeRequiredError
from gridsync.gui import Gui
from gridsync.lock import FilesystemLock
from gridsync.log import LOGGING_ENABLED, initialize_logger
from gridsync.magic_folder import MagicFolder
from gridsync.preferences import get_preference, set_preference
from gridsync.tahoe import Tahoe, get_nodedirs
from gridsync.tor import get_tor
from gridsync.types_ import TwistedDeferred

# mypy thinks reactor is a module
# https://github.com/twisted/twisted/issues/9909
reactor = cast(IReactorCore, reactor_module)


app.setWindowIcon(QIcon(resource(settings["application"]["tray_icon"])))


class Core:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.gateways: list = []
        self.tahoe_version: str = ""
        self.magic_folder_version: str = ""

        if LOGGING_ENABLED:
            initialize_logger(self.args.debug)
        else:
            initialize_logger(self.args.debug, use_null_handler=True)
        # The `Gui` object must be initialized after initialize_logger,
        # otherwise log messages will be duplicated.
        self.gui = Gui(self)

    @staticmethod
    @inlineCallbacks
    def _start_gateway(gateway: Tahoe) -> TwistedDeferred[None]:
        try:
            yield Deferred.fromCoroutine(gateway.start())
        except UpgradeRequiredError as error:
            msg.critical(
                "Invalid configuration detected",
                f"{str(error)}\n\nIn order to continue, you will need to "
                f"either use an older version of {APP_NAME} that is "
                "compatible with your current configuration (not recommended),"
                " or move the existing configuration directory (located at "
                f'"{config_dir}") to a different location and try again.',
            )
        except Exception as e:  # pylint: disable=broad-except
            msg.critical(
                f"Error starting Tahoe-LAFS gateway for {gateway.name}",
                "A critical error occurred when attempting to start the "
                f'Tahoe-LAFS gateway for "{gateway.name}". {APP_NAME} will '
                'now exit.\n\nClick "Show Details..." for more information.',
                str(e),
            )

    async def _get_executable_versions(self) -> None:
        tahoe = Tahoe(enable_logging=False)
        try:
            self.tahoe_version = await tahoe.version()
        except Exception as e:  # pylint: disable=broad-except
            msg.critical(
                "Error getting Tahoe-LAFS version",
                "{}: {}".format(type(e).__name__, str(e)),
            )
        magic_folder = MagicFolder(tahoe, enable_logging=False)
        try:
            self.magic_folder_version = await magic_folder.version()
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
        yield Deferred.fromCoroutine(self._get_executable_versions())

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

        reactor.callLater(0, self.start_gateways)
        # mypy: Argument 2 to "addSystemEventTrigger" of "IReactorCore" has
        # incompatible type "str"; expected "Callable[..., Any]"  [arg-type]
        reactor.addSystemEventTrigger("before", "shutdown", self.stop_gateways)  # type: ignore
        reactor.run()  # type: ignore
        lock.release()
