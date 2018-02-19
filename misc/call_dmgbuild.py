# -*- coding: utf-8 -*-

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import hashlib
import os
import subprocess


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join('gridsync', 'resources', 'config.txt'))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

name = settings['application']['name']
path = 'dist/{}.dmg'.format(name)

subprocess.call(['dmgbuild', '-s', 'misc/dmgbuild_settings.py', name, path])

print("Hashing (SHA256)...")
hasher = hashlib.sha256()
with open(path, 'rb') as f:
    for block in iter(lambda: f.read(4096), b''):
        hasher.update(block)
print("{}  {}".format(hasher.hexdigest(), path))
