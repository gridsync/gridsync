#!/usr/bin/env python3

import os
import sys
from configparser import RawConfigParser
from pathlib import Path
from subprocess import run

config = RawConfigParser(allow_no_value=True)
config.read(Path("gridsync", "resources", "config.txt"))
settings: dict = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

application_name = settings["application"]["name"]
signtool_name = settings["sign"]["signtool_name"]
signtool_sha1 = settings["sign"]["signtool_sha1"]
signtool_timestamp_server = settings["sign"]["signtool_timestamp_server"]

kits_bin = Path(os.environ["PROGRAMFILES(X86)"], "Windows Kits", "10", "bin")
signtools = sorted(list(kits_bin.glob("10.*/x64/signtool.exe")), reverse=True)
if not signtools:
    sys.exit("signtool.exe not found")
signtool_path = str(signtools[0])

paths = [str(p) for p in list(Path("dist", application_name).glob("**/*.exe"))]
paths.extend(
    [str(p) for p in list(Path("dist").glob(application_name + "*.exe"))]
)
if not paths:
    sys.exit("No files to sign; exiting")

for path in paths:
    proc = run(
        [
            signtool_path,
            "sign",
            "/n",
            signtool_name,
            "/sha1",
            signtool_sha1,
            "/tr",
            signtool_timestamp_server,
            "/td",
            "sha256",
            "/fd",
            "sha256",
            path,
        ]
    )
    if proc.returncode:
        sys.exit(f"Error signing {path}")
