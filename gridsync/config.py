# -*- coding: utf-8 -*-

from collections import defaultdict
from configparser import NoOptionError, NoSectionError, RawConfigParser
from typing import Optional

from atomicwrites import atomic_write


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

    def load(self) -> dict:
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        settings_dict: defaultdict = defaultdict(dict)
        for section in config.sections():
            for option, value in config.items(section):
                settings_dict[section][option] = value
        return dict(settings_dict)
