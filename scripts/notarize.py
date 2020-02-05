#!/usr/bin/env python3

import os
import sys
from configparser import RawConfigParser
from pathlib import Path
from subprocess import run, CalledProcessError, SubprocessError
from time import sleep

altool = "/Applications/Xcode.app/Contents/Developer/usr/bin/altool"
stapler = "/Applications/Xcode.app/Contents/Developer/usr/bin/stapler"

# https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow
# https://stackoverflow.com/questions/56890749/macos-notarize-in-script/56890758#56890758
# https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh

# security unlock-keychain login.keychain
# altool --store-password-in-keychain-item gridsync-notarization -u $APPLE_ID -p $APP_SPECIFIC_PASSWORD


def make_zipfile(src_path: str, dst_path: str) -> None:
    run(["ditto", "-c", "-k", "--keepParent", src_path, dst_path])


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


def staple(path: str) -> None:
    p = run([stapler, "staple", path])
    if p.returncode:
        raise SubprocessError(f"Error stapling {path}")


def notarize(path: str, bundle_id: str, username: str, password: str) -> str:
    print(f"Uploading {path} for notarization...")
    uuid = notarize_app(path, bundle_id, username, password)
    print(f"UUID is {uuid}")
    notarized = False
    while not notarized:
        print("Checking status...")
        results = notarization_info(uuid, username, password)
        print(results)
        status = results["Status"]
        if status == "success":
            print(results["Status Message"])
            notarized = True
        elif status == "invalid":
            print(status)
            sys.exit(results["Status Message"])
        else:
            print(status)
            sleep(20)


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
    bundle_id = settings["build"]["mac_bundle_identifier"]

    username = os.environ.get("NOTARIZATION_USERNAME")  # Apple ID
    password = os.environ.get(
        "NOTARIZATION_PASSWORD", "@keychain:gridsync-notarization"
    )

    option = sys.argv[1]
    if option == "app":
        notarize_path = f"dist/{application_name}.zip"
        staple_path = f"dist/{application_name}.app"
        print("Creating ZIP archive...")
        make_zipfile(staple_path, notarize_path)
    elif option == "dmg":
        notarize_path = f"dist/{application_name}.dmg"
        staple_path = f"dist/{application_name}.dmg"

    try:
        notarize(notarize_path, bundle_id, username, password)
    except SubprocessError as err:
        sys.exit(str(err))
    try:
        staple(staple_path)
    except SubprocessError as err:
        sys.exit(str(err))
    print("Success!")
