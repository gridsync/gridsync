# -*- coding: utf-8 -*-

from collections import defaultdict
try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser  # pylint: disable=import-error
import logging
import os
import yaml


class Config(object):
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
        return self.config.get(section, option)

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


class YamlConfig(object):
    def __init__(self, filename):
        self.filename = filename

    def load(self):
        with open(self.filename) as f:
            return yaml.safe_load(f)

    def save(self, settings_dict):
        logging.info("Saving config to %s", self.filename)
        with open(self.filename, 'w') as f:
            os.chmod(self.filename, 0o600)
            yaml.safe_dump(settings_dict, f, encoding='utf-8',
                           allow_unicode=True, default_flow_style=False)
