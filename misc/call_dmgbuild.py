# -*- coding: utf-8 -*-

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import subprocess


config = RawConfigParser(allow_no_value=True)
config.read('config.txt')
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

name = settings['application']['name']
path = 'dist/{}.dmg'.format(name)

subprocess.call(['dmgbuild', '-s', 'misc/dmgbuild_settings.py', name, path])
