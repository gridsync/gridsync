# -*- coding: utf-8 -*-

import logging
import os
import sys
import yaml


class Config():
    def __init__(self, config_file=None):
        if sys.platform == 'win32':
            self.config_dir = os.path.join(os.getenv('APPDATA'), 'Gridsync')
        elif sys.platform == 'darwin':
            self.config_dir = os.path.join(os.path.expanduser('~'), 'Library',
                    'Application Support', 'Gridsync')
        else:
            self.config_dir = os.path.join(os.path.expanduser('~'), '.config',
                    'gridsync')
        if config_file:
            self.config_file = config_file[0]
        else:
            self.config_file = os.path.join(self.config_dir, 'config.yml')

    def load(self):
        with open(self.config_file) as f:
            return yaml.safe_load(f)

    def save(self, dict):
        logging.info('Saving config to {}'.format(self.config_file))
        with open(self.config_file, 'w') as f:
            try:
                os.chmod(self.config_file, 0o600)
            except:
                pass
            yaml.safe_dump(dict, f, encoding='utf-8', allow_unicode=True,
                    indent=4, default_flow_style=False)

