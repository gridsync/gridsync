#!/usr/bin/env python3

from configparser import RawConfigParser
from pathlib import Path
from subprocess import run


config = RawConfigParser(allow_no_value=True)
config.read(Path("gridsync", "resources", "config.txt"))
settings = {}
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        settings[section][option] = value

application_name = settings["application"]["name"]
mac_developer_id = settings["sign"]["mac_developer_id"]

run(
    [
        "codesign",
        "--force",
        "--deep",
        f"--sign=Developer ID Application: {mac_developer_id}",
        "--options=runtime",
        "--entitlements=misc/entitlements.plist",
        f"dist/{application_name}.app",
    ]
)

run(["codesign", "--verify", "--verbose=1", f"dist/{application_name}.app"])

run(["codesign", "--display", "--verbose=4", f"dist/{application_name}.app"])

run(
    [
        "spctl",
        "--assess",
        "--type=exec",
        "--verbose=2",
        f"dist/{application_name}.app",
    ]
)
