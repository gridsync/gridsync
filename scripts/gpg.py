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
gpg_key = settings["sign"]["gpg_key"]

paths = []
for p in Path("dist").glob(application_name + "*.*"):
    path = str(p)
    if not path.endswith(".asc"):
        paths.append(path)
if not paths:
    sys.exit("No files to sign; exiting")


if len(sys.argv) < 2:
    sys.exit(f"Usage: {sys.argv[0]} [--sign] [--verify]")
if sys.argv[1] == "--sign":
    for path in paths:
        proc = run(
            [
                "gpg",
                "--yes",
                "--armor",
                "--detach-sign",
                "--default-key",
                gpg_key,
                path,
            ]
        )
        if proc.returncode:
            sys.exit(f"Error signing {path}")
elif sys.argv[1] == "--verify":
    for path in paths:
        proc = run(["gpg", "--verify", path + ".asc", path])
        if proc.returncode:
            sys.exit(f"Error verifying {path}")
