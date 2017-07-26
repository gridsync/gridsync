# -*- coding: utf-8 -*-

import logging
import os

from gridsync import config_dir
from gridsync.config import Config


def set_preference(section, option, value, config_file=None):
    if not config_file:
        config_file = os.path.join(config_dir, 'preferences.ini')
    config = Config(config_file)
    config.set(section, option, value)
    logging.debug("Set user preference: %s %s %s", section, option, value)


def get_preference(section, option, config_file=None):
    if not config_file:
        config_file = os.path.join(config_dir, 'preferences.ini')
    config = Config(config_file)
    return config.get(section, option)
