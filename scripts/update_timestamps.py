#!/usr/bin/env python3

import os
import subprocess
import sys


def git_timestamp():
    output = subprocess.check_output(["git", "log", "-1", "--pretty=%ct"])
    return int(output.strip())


def update_timestamps(path, timestamp):
    paths = [path]
    for root, directories, files, in os.walk(path):
        for file in files:
            paths.append(os.path.join(root, file))
        for directory in directories:
            paths.append(os.path.join(root, directory))
    for p in paths:
        try:
            os.utime(p, (timestamp, timestamp), follow_symlinks=False)
        except NotImplementedError:  # Windows
            os.utime(p, (timestamp, timestamp))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: {} <path> [timestamp]".format(sys.argv[0]))
    elif len(sys.argv) < 3:
        update_timestamps(sys.argv[1], git_timestamp())
    else:
        update_timestamps(sys.argv[1], int(sys.argv[-1]))
