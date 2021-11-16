#!/usr/bin/env python
# A quick-and-dirty hashin wrapper to facilitate updating requirements/*.txt

from __future__ import print_function

import os
import subprocess

for f in os.listdir("requirements"):
    args = ["python3", "-m", "hashin", "--interactive", "--update-all"]
    pythons = ["3.7", "3.8", "3.9"]
    if f == "lint.txt":
        args.extend(["--include-prereleases"])
    elif f == "pyinstaller.txt":
        pythons.extend(["2.7"])
    elif f == "tahoe-lafs.txt":
        pythons = ["2.7"]
    for python in pythons:
        args.extend(["--python-version", python])
    args.extend(["-r", os.path.join("requirements", f)])
    print(" ".join(args))
    subprocess.call(args)
    print("\n")
