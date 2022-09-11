#!/usr/bin/env python3

import hashlib
import json
import os
import sys
from configparser import RawConfigParser
from pathlib import Path
from secrets import compare_digest
from subprocess import CalledProcessError, SubprocessError, run
from time import sleep
from typing import Optional

altool = "/Applications/Xcode.app/Contents/Developer/usr/bin/altool"
stapler = "/Applications/Xcode.app/Contents/Developer/usr/bin/stapler"

# To setup before use, perform the following steps:
# 1. Unlock the login keychain:
#   security unlock-keychain login.keychain
# 2. Import the codesign ("Developer ID Application") certificate into the login keychain:
#   security import <CERTIFICATE.p12> -k ~/Library/Keychains/login.keychain-db -P <PASSWORD> -T /usr/bin/codesign
# 3. Add an "app-specific password" for notarization to the non-syncable keychain:
#   altool --store-password-in-keychain-item gridsync-notarization -u <APPLE_ID> -p <APP_SPECIFIC_PASSWORD>
# (Note: "altool" is provided by XCode: https://developer.apple.com/download/all/)

# Sources/references:
# https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow
# https://stackoverflow.com/questions/56890749/macos-notarize-in-script/56890758#56890758
# https://github.com/metabrainz/picard/blob/master/scripts/package/macos-notarize-app.sh


def sha256sum(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            hasher.update(block)
    return hasher.hexdigest()


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


def notarize(
    path: str,
    bundle_id: str,
    username: str,
    password: str,
    sha256_hash: Optional[str] = None,
) -> str:
    if sha256_hash:
        print(f"Uploading {path} ({sha256_hash}) for notarization...")
    else:
        print(f"Uploading {path} for notarization...")
    uuid = notarize_app(path, bundle_id, username, password)
    print(f"UUID is {uuid}")
    hash_verified = False
    notarized = False
    print("Awaiting response...")
    while not notarized:
        results = notarization_info(uuid, username, password)
        print(results)
        status = results["Status"]
        if sha256_hash and not hash_verified:
            remote_hash = results.get("Hash")
            if remote_hash:
                if remote_hash == sha256_hash:
                    hash_verified = True
                    print("Hashes match.")
                else:
                    raise Exception(
                        f"Hash mismatch! The local SHA256 hash ({sha256_hash})"
                        f" does not match the remote file ({remote_hash})"
                    )
        if status == "success":
            notarized = True
        elif status == "invalid":
            sys.exit(results["Status Message"])
        else:
            sleep(10)


def store_credentials(
    apple_id: str, password: str, team_id: str, keychain_profile: str
) -> None:
    run(
        [
            "xcrun",
            "notarytool",
            "store-credentials",
            "--apple-id",
            apple_id,
            "--password",
            password,
            "--team-id",
            team_id,
            keychain_profile,
        ]
    )


def notarytool(
    subcommand: str, args: list[str], keychain_profile: str
) -> dict[str, str]:
    proc = run(
        [
            "xcrun",
            "notarytool",
            subcommand,
            f"--keychain-profile={keychain_profile}",
            "--output-format=json",
        ]
        + args,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        raise SubprocessError(proc.stderr.strip())
    if proc.stdout:
        result = json.loads(proc.stdout.strip())
    else:
        return {}
    message = result.get("message")
    if message:
        print("###", message)
    return result


def submit(filepath: str, keychain_profile: str) -> str:  # submission-id
    result = notarytool("submit", [filepath], keychain_profile)
    return result["id"]


def info(submission_id: str, keychain_profile: str) -> dict[str, str]:
    result = notarytool("info", [submission_id], keychain_profile)
    return result


def wait(submission_id: str, keychain_profile: str) -> str:
    result = notarytool("wait", [submission_id], keychain_profile)
    return result["status"]


def log(submission_id: str, keychain_profile: str) -> dict[str, str]:
    result = notarytool("log", [submission_id], keychain_profile)
    return result


def main(path: str, keychain_profile: str) -> None:
    if not path.lower().endswith(".dmg") and not path.lower().endswith(".zip"):
        print("Creating ZIP archive...")
        submission_path = path + ".zip"
        make_zipfile(path, submission_path)
    else:
        submission_path = path
    submitted_hash = sha256sum(submission_path)
    print(f"Uploading {submission_path} ({submitted_hash})...")
    submission_id = submit(submission_path, keychain_profile)
    print(info(submission_id, keychain_profile))
    print("Waiting for result...")
    status = wait(submission_id, keychain_profile)
    result = log(submission_id, keychain_profile)
    print(json.dumps(result, sort_keys=True, indent=2))
    if status != "Accepted":
        sys.exit(f'ERROR: Notarization failed; status: "{status}"')
    notarized_hash = result["sha256"]
    if not compare_digest(submitted_hash, notarized_hash):
        sys.exit(
            "ERROR: SHA-256 hash mismatch\n"
            f"Submitted: {submitted_hash}\n"
            f"Notarized: {submitted_hash}"
        )
    staple(path)
    print("Success!")


if __name__ == "__main__":
    path = sys.argv[1]
    try:
        main(path, "gridsync")
    except Exception as e:
        sys.exit(str(e))
    sys.exit()

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
        "NOTARIZATION_PASSWORD",
        f"@keychain:{application_name.lower()}-notarization",
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

    sha256_hash = sha256sum(notarize_path)
    try:
        notarize(notarize_path, bundle_id, username, password, sha256_hash)
    except SubprocessError as err:
        sys.exit(str(err))
    try:
        staple(staple_path)
    except SubprocessError as err:
        sys.exit(str(err))
    print("Success!")
    if option == "dmg":
        sha256_hash = sha256sum(staple_path)
        print(f"{sha256_hash}  {staple_path}")
