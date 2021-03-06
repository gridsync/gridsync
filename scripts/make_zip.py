#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import sys
import zipfile
from configparser import RawConfigParser


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
app_name = config.get("application", "name")


def make_zip(base_name, root_dir=None, base_dir=None):
    zipfile_path = os.path.abspath(base_name)
    if not root_dir:
        root_dir = os.getcwd()
    if not base_dir:
        base_dir = os.getcwd()

    os.chdir(root_dir)
    paths = []
    for root, directories, files in os.walk(base_dir):
        for file in files:
            paths.append(os.path.join(root, file))
        for directory in directories:
            dirpath = os.path.join(root, directory)
            if os.path.islink(dirpath):
                paths.append(dirpath)
            elif not os.listdir(dirpath):  # Directory is empty
                paths.append(dirpath + "/")

    with zipfile.ZipFile(zipfile_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(paths):
            if path.endswith("/"):
                zf.writestr(zipfile.ZipInfo.from_file(path), "")
            elif os.path.islink(path):
                zinfo = zipfile.ZipInfo.from_file(path)
                zinfo.filename = path
                zinfo.create_system = 3
                zinfo.external_attr = (0o755 | stat.S_IFLNK) << 16
                zf.writestr(zinfo, os.readlink(path))
            else:
                zf.write(path, compresslevel=1)


if sys.platform == "darwin":
    make_zip(
        os.path.join("dist", app_name) + ".zip", "dist", app_name + ".app"
    )
else:
    make_zip(os.path.join("dist", app_name) + ".zip", "dist", app_name)
