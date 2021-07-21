# -*- mode: python ; coding: utf-8 -*-
import sys

# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules["FixTk"] = None

options = [
    # Enable unbuffered stdio:
    ("u", None, "OPTION"),
    # Supress cryptography.io's python2 CryptographyDeprecationWarning:
    ("W ignore::UserWarning", None, "OPTION"),
]

# Get the path to the installed __main__ module.
import inspect
from magic_folder import __main__ as script_module
script_path = inspect.getsourcefile(script_module)

a = Analysis(
    [script_path],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["UserList", "UserString", "commands"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    options,
    exclude_binaries=True,
    name="magic-folder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="magic-folder",
)
