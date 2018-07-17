# -*- coding: utf-8 -*-

from collections import defaultdict
from configparser import RawConfigParser, NoOptionError, NoSectionError


class Config():
    def __init__(self, filename):
        self.filename = filename
        self.config = RawConfigParser(allow_no_value=True)

    def set(self, section, option, value):
        self.config.read(self.filename)
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, value)
        with open(self.filename, 'w') as f:
            self.config.write(f)

    def get(self, section, option):
        self.config.read(self.filename)
        try:
            return self.config.get(section, option)
        except (NoOptionError, NoSectionError):
            return None

    def save(self, settings_dict):
        self.config.read(self.filename)
        for section, d in settings_dict.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
            for option, value in d.items():
                self.config.set(section, option, value)
        with open(self.filename, 'w') as f:
            self.config.write(f)

    def load(self):
        self.config.read(self.filename)
        settings_dict = defaultdict(dict)
        for section in self.config.sections():
            for option, value in self.config.items(section):
                settings_dict[section][option] = value
        return dict(settings_dict)
