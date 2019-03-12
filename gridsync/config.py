# -*- coding: utf-8 -*-

from collections import defaultdict
from configparser import RawConfigParser, NoOptionError, NoSectionError


class Config():
    def __init__(self, filename):
        self.filename = filename

    def set(self, section, option, value):
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)
        with open(self.filename, 'w') as f:
            config.write(f)

    def get(self, section, option):
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        try:
            return config.get(section, option)
        except (NoOptionError, NoSectionError):
            return None

    def save(self, settings_dict):
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        for section, d in settings_dict.items():
            if not config.has_section(section):
                config.add_section(section)
            for option, value in d.items():
                config.set(section, option, value)
        with open(self.filename, 'w') as f:
            config.write(f)

    def load(self):
        config = RawConfigParser(allow_no_value=True)
        config.read(self.filename)
        settings_dict = defaultdict(dict)
        for section in config.sections():
            for option, value in config.items(section):
                settings_dict[section][option] = value
        return dict(settings_dict)
