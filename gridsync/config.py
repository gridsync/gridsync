# -*- coding: utf-8 -*-

import logging
import os
import sys
import yaml


class Config(object):
    def __init__(self, config_file=None):
        if sys.platform == 'win32':
            self.config_dir = os.path.join(os.getenv('APPDATA'), 'Gridsync')
        elif sys.platform == 'darwin':
            self.config_dir = os.path.join(
                os.path.expanduser('~'), 'Library', 'Application Support',
                'Gridsync')
        else:
            basedir = os.environ.get(
                'XDG_CONFIG_HOME',
                os.path.join(os.path.expanduser('~'), '.config'))
            self.config_dir = os.path.join(basedir, 'gridsync')
        if config_file:
            self.config_file = config_file[0]
        else:
            self.config_file = os.path.join(self.config_dir, 'config.yml')

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
