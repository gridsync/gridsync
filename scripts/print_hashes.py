#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import hashlib
import os
import sys


def print_hashes(path, basedir=None):
    files_list = []
    for root, dirs, files in os.walk(path, followlinks=True):
        for name in files:
            if '.git' not in root:
                files_list.append(os.path.join(root, name))
    for filepath in sorted(files_list):
        print(hashlib.sha256(filepath.encode('utf-8')).hexdigest(), filepath)



if __name__ == '__main__':
    print_hashes(sys.argv[1])
