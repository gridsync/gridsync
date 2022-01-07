import glob
import inspect
import os
import re
import shutil
import sys
from configparser import RawConfigParser
from distutils.sysconfig import get_python_lib
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    get_package_paths,
    remove_prefix,
)

from versioneer import get_versions

# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules["FixTk"] = None
excludes = ["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"]


config = RawConfigParser(allow_no_value=True)
config.read(Path("gridsync", "resources", "config.txt"))
settings = {}
print("----------------------- config.txt settings: -----------------------")
for section in config.sections():
    if section not in settings:
        settings[section] = {}
    for option, value in config.items(section):
        print(f"[{section}] {option} = {value}")
        settings[section][option] = value
print("--------------------------------------------------------------------")
app_name = settings["application"]["name"]


version = settings["build"].get("version", get_versions()["version"])
# When running frozen, Versioneer returns a version string of "0+unknown"
# so write the version string from a file that can be read/loaded later.
with open(os.path.join("gridsync", "resources", "version.txt"), "w") as f:
    f.write(version)


if sys.platform == "win32":
    kit = Path(Path.home().anchor, "Program Files (x86)", "Windows Kits", "10")
    paths = [
        str(Path(get_python_lib(), "PyQt5", "Qt", "bin")),
        str(Path(kit, "bin", "x86")),
        str(Path(kit, "bin", "x64")),
        str(Path(kit, "Redist", "ucrc", "DLLs", "x86")),
        str(Path(kit, "Redist", "ucrc", "DLLs", "x64")),
    ]
else:
    paths = []


a = Analysis(
    ["gridsync/cli.py"],
    pathex=paths,
    binaries=None,
    datas=[
        ("gridsync/resources/*", "resources"),
        ("gridsync/resources/providers/*", "resources/providers"),
    ],
    hiddenimports=["cffi", "PyQt5.sip", "pkg_resources.py2_warn"],
    hookspath=["pyinstaller-hooks"],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)


from magic_folder import __main__ as magic_folder_script_module

magic_folder_script_path = inspect.getsourcefile(magic_folder_script_module)
magic_folder_a = Analysis(
    [magic_folder_script_path],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=["UserList", "UserString", "commands"],
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)


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


from allmydata import __main__ as tahoe_script_module

tahoe_script_path = inspect.getsourcefile(tahoe_script_module)
tahoe_a = Analysis(
    [tahoe_script_path],
    pathex=[],
    binaries=collect_dynamic_libs("challenge_bypass_ristretto"),
    datas=collect_data_files("allmydata.web"),
    hiddenimports=[
        "__builtin__",
        "allmydata.client",
        "allmydata.introducer",
        "allmydata.stats",
        "allmydata.web",
        "base64",
        "cffi",
        "collections",
        "commands",
        "Crypto",
        "functools",
        "future.backports.misc",
        "itertools",
        "math",
        "packaging.specifiers",
        "re",
        "reprlib",
        "six.moves.html_parser",
        "subprocess",
        "twisted.plugins.zkapauthorizer",
        "UserDict",
        "UserList",
        "UserString",
        "yaml",
        "zfec",
    ],
    hookspath=["pyinstaller-hooks"],
    runtime_hooks=["pyinstaller-hooks/rthooks/runtime-twisted.plugins.py"],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

MERGE(
    (a, app_name, app_name),
    (magic_folder_a, "magic-folder", "magic-folder"),
    (tahoe_a, "Tahoe-LAFS", "Tahoe-LAFS"),
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=app_name,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.abspath(settings["build"]["win_icon"]),
)


magic_folder_pyz = PYZ(
    magic_folder_a.pure, magic_folder_a.zipped_data, cipher=None
)
magic_folder_exe = EXE(
    magic_folder_pyz,
    magic_folder_a.scripts,
    [("u", None, "OPTION")],  # Enable unbuffered stdio
    exclude_binaries=True,
    name="magic-folder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

tahoe_pyz = PYZ(tahoe_a.pure, tahoe_a.zipped_data, cipher=None)
tahoe_exe = EXE(
    tahoe_pyz,
    tahoe_a.scripts,
    [("u", None, "OPTION")],  # Enable unbuffered stdio
    exclude_binaries=True,
    name="tahoe",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    magic_folder_exe,
    magic_folder_a.binaries,
    magic_folder_a.zipfiles,
    magic_folder_a.datas,
    tahoe_exe,
    tahoe_a.binaries,
    tahoe_a.zipfiles,
    tahoe_a.datas,
    strip=False,
    upx=False,
    name=app_name,
)


mac_background_only = settings["build"].get("mac_background_only", False)
if mac_background_only and mac_background_only.lower() != "false":
    mac_background_only = True

app = BUNDLE(
    coll,
    name=(app_name + ".app"),
    icon=os.path.abspath(settings["build"]["mac_icon"]),
    bundle_identifier=settings["build"]["mac_bundle_identifier"],
    info_plist={
        "CFBundleShortVersionString": version,
        "LSBackgroundOnly": mac_background_only,
        "LSUIElement": mac_background_only,
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)


if sys.platform.startswith("linux"):
    src = os.path.join("dist", app_name, app_name)
    dest = os.path.join("dist", app_name, app_name.lower())
    shutil.move(src, dest)
    bad_libs = [
        "libX11.so.6",  # https://github.com/gridsync/gridsync/issues/43
        "libdrm.so.2",  # https://github.com/gridsync/gridsync/issues/47
        "libstdc++.so.6",  # https://github.com/gridsync/gridsync/issues/189
    ]
    for lib in bad_libs:
        try:
            Path("dist", app_name, lib).unlink(missing_ok=True)
        except Exception as exc:
            print(f"WARNING: Could not delete {lib}: {str(exc)}")
        print(f"Deleted {lib} from bundle")


# The presence of *.dist-info/RECORD files causes issues with reproducible
# builds; see: https://github.com/gridsync/gridsync/issues/363
for p in [p for p in Path("dist", app_name).glob("**/*.dist-info/RECORD")]:
    print(f"Removing {p}...")
    try:
        os.remove(p)
    except Exception as exc:
        print(f"WARNING: Could not remove {p}: {str(exc)}")
