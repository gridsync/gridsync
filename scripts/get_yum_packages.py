#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys


def get_files(appimage_path):
    files = []
    output = subprocess.check_output([appimage_path, "--appimage-extract"])
    for line in output.decode("utf-8").strip().split("\n"):
        files.append(line)
    shutil.rmtree("squashfs-root")
    return sorted(files)


def get_libs(files):
    libs = set()
    for path in files:
        basename = os.path.basename(path)
        if ".so" in basename:
            libs.add(basename)
    return libs


def get_pkg_name(pkg):
    tokens = []
    for token in pkg.split("-"):
        if token.replace(".", "").isdigit():
            break
        else:
            tokens.append(token)
    return "-".join(tokens)


def get_pkg(lib):
    pkg = ""
    output = subprocess.check_output(["yum", "whatprovides", lib])
    for line in output.decode("utf-8").strip().split("\n"):
        if " : " in line:
            w = line.split(" ")[0]
            if "-" in w or w.endswith("i686") or w.endswith("x86_64"):
                pkg = get_pkg_name(w)
    return pkg


def get_pkgs(libs):
    pkgs = set()
    for lib in libs:
        pkg = get_pkg(lib)
        if pkg:
            print("{} -> {}".format(lib, pkg))
            pkgs.add(pkg)
    return pkgs


if __name__ == "__main__":
    argv = sys.argv
    if len(argv) < 2:
        sys.exit("Usage: {} <path to AppImage>".format(argv[0]))
    path = " ".join(argv[1:])

    files = get_files(path)
    for file in files:
        print(file)
    libs = get_libs(files)
    pkgs = get_pkgs(libs)
    for pkg in sorted(list(pkgs)):
        print("    {} \\".format(pkg))
