#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import os
import shutil
import subprocess
import sys

from configparser import RawConfigParser


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value
name = settings["application"]["name"]


def sha256sum(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            hasher.update(block)
    return hasher.hexdigest()


if __name__ == "__main__":
    target = "dist/{}.AppImage".format(name)
    checksum_1 = sha256sum(target)
    subprocess.call(["make", "clean", "all"])
    checksum_2 = sha256sum(target)
    if checksum_1 == checksum_2:
        print("Success! {} was rebuilt reproducibly!".format(target))
    else:
        sys.exit("Hashes don't match ({}, {})".format(checksum_1, checksum_2))
