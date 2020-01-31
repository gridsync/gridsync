#!/usr/bin/env python3

import os
import sys
from configparser import RawConfigParser
from pathlib import Path
from subprocess import run, CalledProcessError, SubprocessError
from time import sleep

altool = "/Applications/Xcode.app/Contents/Developer/usr/bin/altool"
stapler = "/Applications/Xcode.app/Contents/Developer/usr/bin/stapler"

# https://stackoverflow.com/questions/56890749/macos-notarize-in-script/56890758#56890758
# https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh

# security unlock-keychain login.keychain
# altool --store-password-in-keychain-item gridsync-notarization -u $APPLE_ID -p $APP_SPECIFIC_PASSWORD


def notarize_app(
    path: str, bundle_id: str, username: str, password: str
) -> str:
    completed_process = run(
        [
            altool,
            "--notarize-app",
            f"--file={path}",
            f"--primary-bundle-id={bundle_id}",
            f"--username={username}",
            f"--password={password}",
        ],
        capture_output=True,
        text=True,
    )
    stdout = completed_process.stdout.strip()
    stderr = completed_process.stderr.strip()
    if completed_process.returncode or stderr:
        s = "The software asset has already been uploaded. The upload ID is "
        if s in stderr:
            print(f"{path} has already been uploaded")
            start = stderr.index(s) + len(s)
            uuid = stderr[start : start + 36]
            return uuid
        raise SubprocessError(stderr)
    if stdout.startswith("No errors uploading"):
        uuid = stdout.split()[-1]
        return uuid


def notarization_info(uuid: str, username: str, password: str) -> dict:
    completed_process = run(
        [
            altool,
            "--notarization-info",
            uuid,
            f"--username={username}",
            f"--password={password}",
        ],
        capture_output=True,
        text=True,
    )
    stdout = completed_process.stdout.strip()
    stderr = completed_process.stderr.strip()
    if completed_process.returncode or stderr:
        raise SubprocessError(stderr)
    results = {}
    for line in stdout.split("\n"):
        if line:
            split = line.split(":")
            key = split[0].strip()
            value = ":".join(split[1:]).strip()
            if key and value:
                results[key] = value
    return results


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
    path = f"dist/{application_name}.dmg"
    bundle_id = settings["build"]["mac_bundle_identifier"]

    username = os.environ.get("NOTARIZATION_USERNAME")  # Apple ID
    password = os.environ.get(
        "NOTARIZATION_PASSWORD", "@keychain:gridsync-notarization"
    )

    print(f"Uploading {path} for notarization...")
    try:
        uuid = notarize_app(path, bundle_id, username, password)
    except SubprocessError as err:
        sys.exit(str(err))
    print(f"UUID is {uuid}")
    notarized = False
    while not notarized:
        print("Checking status...")
        try:
            results = notarization_info(uuid, username, password)
        except SubprocessError as err:
            sys.exit(str(err))
        print(results)
        status = results["Status"]
        if status == "success":
            print(results["Status Message"])
            notarized = True
        else:
            print(status)
            sleep(20)
    print("Success!")
