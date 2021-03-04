# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import subprocess
import sys


def check_outdated(pip_path, env_name):
    out = subprocess.check_output(
        [pip_path, "list", "--outdated"],
        env={
            "PYTHONWARNINGS": "ignore:DEPRECATION::pip._internal.cli.base_command"
        },
    ).decode()
    outdated = []
    for line in out.strip().split("\n"):
        if (
            not line.startswith("Package")
            and not line.startswith("-")
            and not line.startswith("pip ")
            and not line.startswith("setuptools ")
        ):
            outdated.append(line)
    return (env_name, outdated)


def get_virtualenvs():
    envs = []
    if sys.platform == "win32":
        bindir = "Scripts"
        pipexe = "pip.exe"
    else:
        bindir = "bin"
        pipexe = "pip"
    for dirname in os.listdir(".tox"):
        pip_path = os.path.join(".tox", dirname, bindir, pipexe)
        if os.path.exists(pip_path):
            envs.append((dirname, pip_path))
    tahoe_pip_path = os.path.join("build", "venv-tahoe", bindir, pipexe)
    if os.path.exists(tahoe_pip_path):
        envs.append(("tahoe-lafs", tahoe_pip_path))
    return sorted(envs)


def main():
    results = []
    for env_name, pip_path in get_virtualenvs():
        results.append(check_outdated(pip_path, env_name))
    for env_name, outdated in results:
        if outdated:
            print("\n" + env_name + ":\n-------------------------------")
            for package in outdated:
                print(package)


if __name__ == "__main__":
    main()
