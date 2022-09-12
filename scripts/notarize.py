#!/usr/bin/env python3
# This script assumes/requires credentials stored in a keychain profile.
# To store credentials in a keychain profile programmatically:
# xcrun notarytool store-credentials <PROFILE-NAME> [--apple-id <APPLE-ID>] [--team-id <TEAM-ID>] [--password <APP-SPECIFIC-PASSWORD>]
# Sources/references:
# https://developer.apple.com/documentation/xcode/notarizing_macos_software_before_distribution/customizing_the_notarization_workflow
# https://stackoverflow.com/questions/56890749/macos-notarize-in-script/56890758#56890758
import hashlib
import json
import os
import sys
from configparser import RawConfigParser
from pathlib import Path
from secrets import compare_digest
from subprocess import SubprocessError, run


def sha256sum(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            hasher.update(block)
    return hasher.hexdigest()


def make_zipfile(src_path: str, dst_path: str) -> None:
    run(["ditto", "-c", "-k", "--keepParent", src_path, dst_path], check=True)


def staple(filepath: str) -> None:
    run(["xcrun", "stapler", "staple", filepath], check=True)


def notarytool(
    subcommand: str, argument: str, keychain_profile: str
) -> dict[str, str]:
    proc = run(
        [
            "xcrun",
            "notarytool",
            subcommand,
            f"--keychain-profile={keychain_profile}",
            "--output-format=json",
            argument,
        ],
        capture_output=True,
        check=False,
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
    result = notarytool("submit", filepath, keychain_profile)
    return result["id"]


def wait(submission_id: str, keychain_profile: str) -> str:  # status
    result = notarytool("wait", submission_id, keychain_profile)
    return result["status"]


def log(submission_id: str, keychain_profile: str) -> dict[str, str]:
    result = notarytool("log", submission_id, keychain_profile)
    return result


def notarize(filepath: str, keychain_profile: str) -> None:
    if not path.lower().endswith(".dmg") and not path.lower().endswith(".zip"):
        print("Creating ZIP archive...")
        submission_path = filepath + ".zip"
        make_zipfile(filepath, submission_path)
    else:
        submission_path = filepath
    submitted_hash = sha256sum(submission_path)
    print(f"Uploading {submission_path} (SHA-256: {submitted_hash})...")
    submission_id = submit(submission_path, keychain_profile)
    print(f"Waiting for result (Submission ID: {submission_id})...")
    status = wait(submission_id, keychain_profile)
    result = log(submission_id, keychain_profile)
    print(json.dumps(result, sort_keys=True, indent=2))
    if status != "Accepted":
        raise Exception(f'ERROR: Notarization failed (status: "{status}")')
    notarized_hash = result["sha256"]
    if not compare_digest(submitted_hash, notarized_hash):
        raise ValueError(
            "ERROR: SHA-256 hash digest mismatch\n"
            f"Submitted: {submitted_hash}\n"
            f"Notarized: {notarized_hash}"
        )
    staple(filepath)
    print("Success!")


def _get_application_name() -> str:
    config = RawConfigParser()
    config.read(Path("gridsync", "resources", "config.txt"))
    return config.get("application", "name")


if __name__ == "__main__":
    try:
        path = sys.argv[1]
    except IndexError:
        path = os.environ.get("NOTARIZATION_PATH", "")
        if not path:
            sys.exit(f"Usage {sys.argv[0]} <filepath | app | dmg>")
    application_name = ""
    if path in ("app", "dmg"):
        try:
            application_name = _get_application_name()
        except Exception:
            sys.exit("Error: Could not load application name from config.txt")
        path = f"dist/{application_name}.{path}"
    if not Path(path).exists():
        sys.exit(f"Error: Path {path} does not exist")
    profile = os.environ.get("NOTARIZATION_PROFILE", application_name)
    if not profile:
        sys.exit(
            "Error: Keychain profile not found; please set the "
            "NOTARIZATION_PROFILE environment variable to the desired "
            "keychain profile name and try again."
        )
    try:
        notarize(path, profile)
    except Exception as e:
        sys.exit(str(e))
