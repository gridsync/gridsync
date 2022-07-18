# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import attr

from gridsync.desktop import notify
from gridsync.gui.debug import DebugExporter
from gridsync.gui.main_window import MainWindow
from gridsync.gui.preferences import PreferencesWindow
from gridsync.gui.systray import SystemTrayIcon
from gridsync.gui.welcome import WelcomeDialog
from gridsync.preferences import Preferences

if TYPE_CHECKING:
    from gridsync.core import Core


class AbstractGui(Protocol):
    core: Core

    welcome_dialog: WelcomeDialog
    main_window: MainWindow
    unread_messages: list[tuple]
    systray: SystemTrayIcon

    def show(self) -> None:
        pass

    def show_preferences_window(self) -> None:
        pass

    def show_debug_exporter(self) -> None:
        pass

    def show_message(
        self, title: str, message: str, duration: int = 5000
    ) -> None:
        pass

    def show_main_window(self) -> None:
        pass

    def populate(self, gateways: list) -> None:
        pass


@attr.s(eq=False)  # To avoid "TypeError: unhashable type: 'Gui'" on PySide2
class Gui:
    core: Core = attr.ib()

    preferences: Preferences = attr.ib(default=attr.Factory(Preferences))
    unread_messages: list[tuple] = attr.ib(default=attr.Factory(list))

    welcome_dialog: WelcomeDialog = attr.ib()
    main_window: MainWindow = attr.ib()
    preferences_window: PreferencesWindow = attr.ib()
    systray: SystemTrayIcon = attr.ib()
    debug_exporter: DebugExporter = attr.ib()

    @welcome_dialog.default
    def _default_welcome_dialog(self) -> WelcomeDialog:
        return WelcomeDialog(self, [])

    @main_window.default
    def _main_window_default(self) -> MainWindow:
        return MainWindow(self)

    @preferences_window.default
    def _default_preferences_window(self) -> PreferencesWindow:
        return PreferencesWindow(self.preferences)

    @systray.default
    def _systray_default(self) -> SystemTrayIcon:
        return SystemTrayIcon(self)

    @debug_exporter.default
    def _debug_exporter_default(self) -> DebugExporter:
        return DebugExporter(self.core)

    def show_message(
        self, title: str, message: str, duration: int = 5000
    ) -> None:
        notify(self.systray, title, message, duration)

    def show_welcome_dialog(self) -> None:
        self.welcome_dialog.showNormal()
        self.welcome_dialog.show()
        self.welcome_dialog.raise_()
        self.welcome_dialog.activateWindow()

    def show_main_window(self) -> None:
        self.main_window.showNormal()
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def show_preferences_window(self) -> None:
        self.preferences_window.showNormal()
        self.preferences_window.show()
        self.preferences_window.raise_()
        self.preferences_window.activateWindow()

    def show_systray(self) -> None:
        if self.systray.isSystemTrayAvailable():
            self.systray.show()
        else:
            self.show_main_window()

    def show(self) -> None:
        self.systray.show()
        if self.main_window.gateways:
            self.show_main_window()
        else:
            self.show_welcome_dialog()

    def hide(self) -> None:
        self.systray.hide()
        self.main_window.hide()
        self.preferences_window.hide()

    def toggle(self) -> None:
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.show_main_window()

    def populate(self, gateways: list) -> None:
        self.main_window.populate(gateways)

    def show_debug_exporter(self) -> None:
        self.debug_exporter.show()
        self.debug_exporter.raise_()
        self.debug_exporter.load()
