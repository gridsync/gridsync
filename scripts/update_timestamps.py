#!/usr/bin/env python3

from __future__ import print_function

import os
import subprocess
import sys


def git_timestamp():
    output = subprocess.check_output(["git", "log", "-1", "--pretty=%ct"])
    return int(output.strip())


def update_timestamps(path, timestamp):
    for root, directories, files, in os.walk(path):
        for file in files:
            os.utime(
                os.path.join(root, file),
                (timestamp, timestamp),
                follow_symlinks=False
            )
        for directory in directories:
            os.utime(
                os.path.join(root, directory),
                (timestamp, timestamp),
                follow_symlinks=False
            )
    os.utime(path, (timestamp, timestamp))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: {} <path> [timestamp]".format(sys.argv[0]))
    elif len(sys.argv) < 3:
        update_timestamps(sys.argv[1], git_timestamp())
    else:
        update_timestamps(sys.argv[1], int(sys.argv[-1]))
