# -*- mode: python -*-

from __future__ import print_function

from distutils.sysconfig import get_python_lib
import sys

from PyInstaller.utils.hooks import collect_data_files


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules['FixTk'] = None

options = [
    # Enable unbuffered stdio:
    ('u', None, 'OPTION'),
    # Supress CryptographyDeprecationWarning (https://github.com/gridsync/gridsync/issues/313):
    ('W ignore::UserWarning', None, 'OPTION')
]

added_files = collect_data_files("allmydata.web")

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
    binaries=None,
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
