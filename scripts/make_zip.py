#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import os
import zipfile


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
app_name = config.get("application", "name")
#shutil.make_archive(os.path.join("dist", app_name), "zip", "dist", app_name)

def make_zip(base_name, root_dir=None, base_dir=None):
    zipfile_path = os.path.abspath(base_name)
    if not root_dir:
        root_dir = os.getcwd()
    if not base_dir:
        base_dir = os.getcwd()

    os.chdir(root_dir)
    paths = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            paths.append(os.path.join(root, file))
    with zipfile.ZipFile(zipfile_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(paths):
            zf.write(path)

make_zip(os.path.join("dist", app_name) + ".zip", "dist", app_name)
