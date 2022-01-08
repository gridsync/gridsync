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

try:
    import allmydata
except ImportError:
    allmydata = None

try:
    import magic_folder
except ImportError:
    magic_folder = None


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
version_file = Path("gridsync", "resources", "version.txt")
# When running frozen, Versioneer returns a version string of "0+unknown"
# so write the real version string to a file that can be read at runtime.
with open(version_file, "w") as f:
    f.write(version)


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules["FixTk"] = None
excludes = ["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"]


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


bundles = []

def collect_dynamic_libs(package):
    """
    This is a version of :py:`PyInstaller.utils.hooks.collect_dynamic_libs`
    that will include linux shared libraries without a `lib` prefix.

    It also only handles dynamic libraries in the root of the package.
    """
    base_path, pkg_path = get_package_paths(package)
    pkg_rel_path = remove_prefix(pkg_path, base_path)
    dylibs = []
    for lib_ext in ["*.dll", "*.dylib", "*.pyd", "*.so"]:
        for file in glob.glob(os.path.join(pkg_path, lib_ext)):
            dylibs.append((file, pkg_rel_path))
    return dylibs

if allmydata:
    from allmydata import __main__ as tahoe_script_module

    tahoe_a = Analysis(
        [inspect.getsourcefile(tahoe_script_module)],
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
    bundles.append((tahoe_a, "tahoe", "tahoe"))

if magic_folder:
    from magic_folder import __main__ as magic_folder_script_module

    magic_folder_a = Analysis(
        [inspect.getsourcefile(magic_folder_script_module)],
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
    bundles.append((magic_folder_a, "magic-folder", "magic-folder"))

if bundles:
    # https://pyinstaller.readthedocs.io/en/stable/spec-files.html#multipackage-bundles
    bundles.insert(0, (a, app_name, app_name))
    MERGE(*bundles)


files = [
    EXE(
        PYZ(a.pure, a.zipped_data, cipher=None),
        a.scripts,
        exclude_binaries=True,
        name=app_name,
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=os.path.abspath(settings["build"]["win_icon"]),
    ),
    a.binaries,
    a.zipfiles,
    a.datas,
]

if allmydata:
    files += [
        EXE(
            PYZ(tahoe_a.pure, tahoe_a.zipped_data, cipher=None),
            tahoe_a.scripts,
            [("u", None, "OPTION")],  # Enable unbuffered stdio
            exclude_binaries=True,
            name="tahoe",
            debug=False,
            strip=False,
            upx=False,
            console=True,
        ),
        tahoe_a.binaries,
        tahoe_a.zipfiles,
        tahoe_a.datas,
    ]

if magic_folder:
    files += [
        EXE(
            PYZ(magic_folder_a.pure, magic_folder_a.zipped_data, cipher=None),
            magic_folder_a.scripts,
            [("u", None, "OPTION")],  # Enable unbuffered stdio
            exclude_binaries=True,
            name="magic-folder",
            debug=False,
            bootloader_ignore_signals=False,
            strip=False,
            upx=False,
            console=True,
        ),
        magic_folder_a.binaries,
        magic_folder_a.zipfiles,
        magic_folder_a.datas,
    ]

mac_background_only = settings["build"].get("mac_background_only", False)
if mac_background_only and mac_background_only.lower() != "false":
    mac_background_only = True

BUNDLE(
    COLLECT(*files, strip=False, upx=False, name=app_name),
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


paths_to_remove = [version_file]

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
        paths_to_remove.append(Path("dist", app_name, lib))

# The presence of *.dist-info/RECORD files causes issues with reproducible
# builds; see: https://github.com/gridsync/gridsync/issues/363
paths_to_remove.extend(
    [path for path in Path("dist", app_name).glob("**/*.dist-info/RECORD")]
)

for path in paths_to_remove:
    if path.exists():
        print(f"Removing {path}...")
        path.unlink()
