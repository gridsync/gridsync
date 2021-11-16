# -*- mode: python -*-

from __future__ import print_function

import glob
import os
import sys
from distutils.sysconfig import get_python_lib

from PyInstaller.utils.hooks import (
    collect_data_files,
    get_package_paths,
    remove_prefix,
)

# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules['FixTk'] = None

options = [
    # Enable unbuffered stdio:
    ('u', None, 'OPTION'),
    # Supress CryptographyDeprecationWarning (https://github.com/gridsync/gridsync/issues/313):
    ('W ignore::UserWarning', None, 'OPTION')
]

added_files = collect_data_files("allmydata.web")


def collect_dynamic_libs(package):
    """
    This is a version of :py:`PyInstaller.utils.hooks.collect_dynamic_libs` that
    will include linux shared libraries without a `lib` prefix.

    It also only handles dymaic libraries in the root of the package.
    """
    base_path, pkg_path = get_package_paths(package)
    pkg_rel_path = remove_prefix(pkg_path, base_path)
    dylibs = []
    for lib_ext in ["*.dll", "*.dylib", "*.pyd", "*.so"]:
        for file in glob.glob(os.path.join(pkg_path, lib_ext)):
            dylibs.append((file, pkg_rel_path))
    return dylibs


binaries = collect_dynamic_libs("challenge_bypass_ristretto")

hidden_imports = [
    '__builtin__',
    'allmydata.client',
    'allmydata.introducer',
    'allmydata.stats',
    'allmydata.web'
    'base64',
    'cffi',
    'collections',
    'commands',
    'Crypto',
    'functools',
    'future.backports.misc',
    'itertools',
    'math',
    'packaging.specifiers',
    're',
    'reprlib',
    'six.moves.html_parser',
    'subprocess',
    'twisted.plugins.zkapauthorizer',
    'UserDict',
    'UserList',
    'UserString',
    'yaml',
    'zfec',
]

a = Analysis(
    ["../../misc/tahoe.py"],
    pathex=[],
    binaries=binaries,
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=["../../pyinstaller-hooks"],
    runtime_hooks=["../../pyinstaller-hooks/runtime-twisted.plugins.py"],
    excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    options,
    exclude_binaries=True,
    name='tahoe',
    debug=False,
    strip=False,
    upx=False,
    console=True)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='Tahoe-LAFS')
