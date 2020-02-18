#!/usr/bin/env python3

import shutil
import sys
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory


src = sys.argv[1]
dst = sys.argv[2]

with TemporaryDirectory() as tmpdir:
    run(["hdiutil", "attach", "-mountpoint", tmpdir, src])
    for app_src in list(Path(tmpdir).glob("*.app")):
        app_dst = Path(dst, Path(app_src).name)
        shutil.rmtree(app_dst, ignore_errors=True)
        shutil.copytree(app_src, app_dst, symlinks=True)
    run(["hdiutil", "unmount", tmpdir])
