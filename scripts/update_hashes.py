#!/usr/bin/env python
# A quick-and-dirty hashin wrapper to facilitate updating requirements/*.txt

from __future__ import print_function

import os
import subprocess
from pathlib import Path

REQUIREMENTS_DIR = Path(__file__).parent.with_name("requirements")

for f in REQUIREMENTS_DIR.iterdir():
    args = ["python3", "-m", "hashin", "--interactive", "--update-all"]
    pythons = ["3.7", "3.8", "3.9"]
    if f.suffix != ".txt":
        continue
    if f.name == "lint.txt":
        args.extend(["--include-prereleases"])
    elif f.name == "pyinstaller.txt":
        pythons.extend(["2.7"])
    elif f.name.startswith("tahoe-lafs"):
        # tahoe-lafs dependencies are handled elsewhere.
        continue
    for python in pythons:
        args.extend(["--python-version", python])
    args.extend(["-r", os.path.join("requirements", f)])
    print(" ".join(args))
    subprocess.call(args)
    print("\n")
