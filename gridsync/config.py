# -*- coding: utf-8 -*-

from collections import defaultdict
from configparser import NoOptionError, NoSectionError, RawConfigParser
from typing import Optional

from atomicwrites import atomic_write
from typing_extensions import TypeAlias

Settings: TypeAlias = dict[str, dict[str, str]]


class Config:
    def __init__(self, filename: str) -> None:
        self.filename = filename

    def set(self, section: str, option: str, value: str) -> None:
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        with atomic_write(self.filename, mode="w", overwrite=True) as f:
            config.write(f)

    def get(self, section: str, option: str) -> Optional[str]:
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        try:
            return config.get(section, option)
        except (NoOptionError, NoSectionError):
            return None

    def save(self, settings_dict: dict) -> None:
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        for section, d in settings_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            for option, value in d.items():
                config.set(section, option, value)
        with atomic_write(self.filename, mode="w", overwrite=True) as f:
            config.write(f)

    def load(self) -> dict[str, dict[str, str]]:
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        settings_dict: defaultdict = defaultdict(dict)
        for section in config.sections():
            for option, value in config.items(section):
                settings_dict[section][option] = value
        return dict(settings_dict)


def get_log_maxlen(settings: Settings) -> int:
    """
    Get the configured maximum for the number of log records to retain.

    If none is configured a default is supplied.
    """
    log_maxlen = settings.get("debug", {}).get("log_maxlen", None)
    if log_maxlen is None:
        return 100000  # XXX
    return int(log_maxlen)


def get_application_icon_resource_name(settings: Settings) -> tuple[bool, str]:
    """
    Get the configured application icon resource name, using either the logo
    icon configuration or the tray icon configuration.

    :return: A tuple of true and the name if the logo icon is found or false
        and the name if the tray icon is used.
    """
    application = settings["application"]
    logo_icon = application.get("logo_icon")
    if logo_icon is not None:
        return True, logo_icon

    tray_icon = application.get("tray_icon")
    if tray_icon is None:
        raise ValueError("Configuration has neither logo_icon nor tray_icon")
    return False, tray_icon


def get_application_description(settings: Settings) -> str:
    """
    Get the configured application description.
    """
    return settings.get("application", {}).get("description", "")


def get_default_connection_code(settings: Settings) -> Optional[str]:
    """
    Get the configured default connection "cheatcode", if there is one.
    """
    return settings.get("connection", {}).get("default", None)


def get_startup_warning_message(
    settings: Settings,
) -> Optional[tuple[Optional[str], str, str]]:
    """
    Get the configured scary startup-time warning message, if there is
    one.
    """
    message_settings = settings.get("message")
    if message_settings is None:
        return None

    return (
        message_settings.get("type"),
        message_settings["title"],
        message_settings["text"],
    )
