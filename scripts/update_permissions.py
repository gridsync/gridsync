#!/usr/bin/env python3
# Some distros (ubuntu-20.04, debian-10) have a default umask of 022
# while others (ubuntu-20.10, fedora-32) use 0002. Normalizing this
# helps with deterministic/reproducible builds.

import os
import sys


def update_permissions(path):
    for root, directories, files, in os.walk(path):
        for file in files:
            filepath = os.path.join(root, file)
            if os.access(filepath, os.X_OK):
                os.chmod(filepath, 0o755)
            else:
                os.chmod(filepath, 0o644)
        for directory in directories:
            os.chmod(os.path.join(root, directory), 0o755)
    os.chmod(path, 0o755)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: {} <path>".format(sys.argv[0]))
    else:
        update_permissions(sys.argv[1])
