#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser
import os
import shutil
import sys


def main():
    config = RawConfigParser(allow_no_value=True)
    config.read(os.path.join('gridsync', 'resources', 'config.txt'))
    app_name = config.get('application', 'name')
    base_name = os.path.join('dist', app_name)
    if sys.platform == 'win32':
        format = 'zip'
        suffix = '.zip'
    else:
        format = 'gztar'
        suffix = '.tar.gz'
    print("Creating archive: " + base_name + suffix)
    shutil.make_archive(base_name, format, 'dist', app_name)
    print("Done!")


if __name__ == '__main__':
    main()
