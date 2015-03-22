#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from __future__ import unicode_literals

import os
import json


class Config():
    def __init__(self, config_file=None):
        if os.name == 'nt':
            self.config_dir = os.path.join(os.getenv('APPDATA'), 'gridsync')
        else:
            self.config_dir = os.path.join(os.path.expanduser('~'), '.config', 'gridsync')
        if not os.path.isdir(self.config_dir):
            #first run
            os.makedirs(self.config_dir)
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.path.join(self.config_dir, 'settings.json')

    def load(self):
        with open(self.config_file) as f:
            return json.load(f)

    def save(self, dict):
        print('*** Saving config')
        with open(self.config_file, 'w') as f:
            json.dump(dict, f, indent=4)


