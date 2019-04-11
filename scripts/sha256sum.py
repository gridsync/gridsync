#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import glob
import hashlib
import os
import sys


def sha256sum(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            hasher.update(block)
    return hasher.hexdigest()


def main():
    paths = []
    for arg in sys.argv[1:]:
        paths.extend(glob.glob(arg))

    filepaths = []
    for path in paths:
        if os.path.isdir(path):
            for root, _, files, in os.walk(path, followlinks=True):
                for name in files:
                    filepaths.append(os.path.join(root, name))
        else:
            filepaths.append(path)

    for filepath in sorted(filepaths):
        print("{}  {}".format(sha256sum(filepath), filepath))


if __name__ == '__main__':
    main()
