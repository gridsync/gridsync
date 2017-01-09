# -*- coding: utf-8 -*-

import logging
import os
import yaml


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
