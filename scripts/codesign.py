#!/usr/bin/env python3

from configparser import RawConfigParser
from pathlib import Path
from subprocess import run
import sys


def codesign_app(developer_id: str, path: str) -> None:
    run(
        [
            "codesign",
            "--force",
            "--deep",
            f"--sign=Developer ID Application: {developer_id}",
            "--timestamp",
            "--options=runtime",
            "--entitlements=misc/entitlements.plist",
            path,
        ]
    )

def codesign_dmg(developer_id: str, path: str) -> None:
    run(
        [
            "codesign",
            "--force",
            "--deep",
            f"--sign=Developer ID Application: {developer_id}",
            "--timestamp",
            path,
        ]
    )

def codesign_verify(path: str):
    run(["codesign", "--verify", "--verbose=1", path])

def codesign_display(path: str):
    run(["codesign", "--display", "--verbose=4", path])

def spctl_assess_app(path: str):
    run(
        [
            "spctl",
            "-vv",
            "--assess",
            "--type=exec",
            path,
        ]
    )

def spctl_assess_dmg(path: str):
    run(
        [
            "spctl",
            "-vv",
            "--assess",
            "--type=open",
            "--context=context:primary-signature",
            path,
        ]
    )


if __name__ == "__main__":
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

    option = sys.argv[1]
    if option == "app":
        path = f"dist/{application_name}.app"
        codesign_app(mac_developer_id, path)
        codesign_verify(path)
        codesign_display(path)
        spctl_assess_app(path)
    elif option == "dmg":
        path = f"dist/{application_name}.dmg"
        codesign_dmg(mac_developer_id, path)
        codesign_verify(path)
        codesign_display(path)
        spctl_assess_dmg(path)
    else:
        sys.exit(f"Unknown option: {option}")
