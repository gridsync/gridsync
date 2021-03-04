#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import os
import shutil


config = RawConfigParser(allow_no_value=True)
config.read(os.path.join("gridsync", "resources", "config.txt"))
app_name = config.get("application", "name")
shutil.make_archive(os.path.join("dist", app_name), "zip", "dist", app_name)
