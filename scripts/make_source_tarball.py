#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import sys
import tarfile
import tempfile
from configparser import RawConfigParser


ignore_patterns = [
    ".cache",
    ".coverage",
    ".eggs",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "build",
    "dist",
    "htmlcov",
]


def should_ignore(path):
    for pattern in ignore_patterns:
        if path.startswith(pattern) or f"__pycache__{os.sep}" in path:
            return True
    return False


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value
name = settings["application"]["name"]

tarball = f"dist{os.sep}{name}.tar.gz"

try:
    os.remove(tarball)
except OSError:
    pass

os.makedirs("dist", exist_ok=True)

with tarfile.open(tarball, "x:gz") as archive:
    filepaths = []
    for dirpath, _, filenames in os.walk(os.getcwd()):
        for filename in filenames:
            relpath = os.path.relpath(os.path.join(dirpath, filename))
            if not should_ignore(relpath):
                filepaths.append(relpath)
    for filepath in sorted(filepaths):
        print(f"Adding {filepath}")
        archive.add(filepath, f"{name}{os.sep}{filepath}")
    print("Done!")
