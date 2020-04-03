# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import subprocess


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


def main():
    tox_envs = subprocess.check_output(["python3", "-m", "tox", "-a"]).decode()
    results = []
    for env in tox_envs.strip().split("\n"):
        results.append(
            check_outdated(os.path.join(".tox", env, "bin", "pip"), env)
        )
    results.append(
        check_outdated(
            os.path.join("build", "venv-tahoe", "bin", "pip"), "tahoe-lafs"
        )
    )
    for env_name, outdated in results:
        if outdated:
            print("\n" + env_name + ":\n-------------------------------")
            for package in outdated:
                print(package)


if __name__ == "__main__":
    main()
