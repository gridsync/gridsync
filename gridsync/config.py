# -*- coding: utf-8 -*-

import logging
import os
import yaml

from gridsync import config_dir


class Config(object):
    def __init__(self, config_file=None):
        self.config_file = config_file
        if not self.config_file:
            self.config_file = os.path.join(config_dir, 'config.yml')

    def load(self):
        with open(self.config_file) as f:
            return yaml.safe_load(f)

    def save(self, settings_dict):
        logging.info("Saving config to %s", self.config_file)
        with open(self.config_file, 'w') as f:
            # TODO: Handle possible exceptions in Core()
            os.chmod(self.config_file, 0o600)
            yaml.safe_dump(settings_dict, f, encoding='utf-8',
                           allow_unicode=True, default_flow_style=False)
