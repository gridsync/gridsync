import inspect
import os
import shutil
import subprocess
import sys
from configparser import RawConfigParser
from distutils.sysconfig import get_python_lib
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    get_package_paths,
    remove_prefix,
)

try:
    # Because Magic-Folder also depends on "allmydata" -- but does not depend
    # on ZKAPAuthorizer. This can be used to indicate whether the requirements
    # declared by `requirements/tahoe-lafs.txt` have been installed directly.
    import _zkapauthorizer as tahoe_available
except ImportError:
    tahoe_available = False

try:
    import magic_folder as magic_folder_available
except ImportError:
    magic_folder_available = False

try:
    import gridsync as gridsync_available
except ImportError:
    gridsync_available = False


# https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
sys.modules["FixTk"] = None


def git_timestamp():
    output = subprocess.check_output(["git", "log", "-1", "--pretty=%ct"])
    return int(output.strip())


if not os.environ.get("SOURCE_DATE_EPOCH"):
    try:
        timestamp = git_timestamp()
    except (OSError, ValueError):
        timestamp = 1641774040
        print(
            "Warning: Could not get timestamp from git; falling back to "
            f"SOURCE_DATE_EPOCH={timestamp}"
        )
    # Required for reprocudible builds on Windows. See
    # https://github.com/pyinstaller/pyinstaller/pull/6469
    os.environ["SOURCE_DATE_EPOCH"] = str(timestamp)


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
import os
from pprint import pprint

pprint(dict(os.environ))
print("--------------------------------------------------------------------")
app_name = settings["application"]["name"]


gridsync_version_file = Path("gridsync", "resources", "version.txt")


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
        for path in Path(pkg_path).glob(lib_ext):
            dylibs.append((str(path.resolve()), pkg_rel_path))
    return dylibs


def analyze_tahoe():
    from allmydata import __main__ as script_module

    return Analysis(
        [inspect.getsourcefile(script_module)],
        pathex=[],
        binaries=collect_dynamic_libs("challenge_bypass_ristretto"),
        datas=collect_data_files("allmydata.web"),
        hiddenimports=[
            "__builtin__",
            "_zkapauthorizer",
            "allmydata.client",
            "allmydata.introducer",
            "allmydata.stats",
            "allmydata.web",
            "base64",
            "certifi",
            "cffi",
            "collections",
            "functools",
            "future.backports.misc",
            "itertools",
            "math",
            "re",
            "reprlib",
            "six.moves.html_parser",
            "subprocess",
            "twisted.plugins.zkapauthorizer",
            "UserDict",
            "yaml",
            "zfec",
        ],
        hookspath=["pyinstaller-hooks"],
        runtime_hooks=["pyinstaller-hooks/rthooks/runtime-twisted.plugins.py"],
        excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=None,
    )


def analyze_magic_folder():
    from magic_folder import __main__ as script_module

    return Analysis(
        [inspect.getsourcefile(script_module)],
        pathex=[],
        binaries=[],
        datas=[],
        hiddenimports=["win32com.shell"],
        hookspath=[],
        runtime_hooks=[],
        excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=None,
        noarchive=False,
    )


def analyze_gridsync():
    from versioneer import get_versions

    version = settings["build"].get("version", get_versions()["version"])
    # When running frozen, Versioneer returns a version string of "0+unknown"
    # so write the real version string to a file that can be read at runtime.
    with open(gridsync_version_file, "w") as f:
        f.write(version)

    if sys.platform == "win32":
        kit = Path(
            Path.home().anchor, "Program Files (x86)", "Windows Kits", "10"
        )
        paths = [
            str(Path(get_python_lib(), "PyQt5", "Qt", "bin")),
            str(Path(kit, "bin", "x86")),
            str(Path(kit, "bin", "x64")),
            str(Path(kit, "Redist", "ucrt", "DLLs", "x86")),
            str(Path(kit, "Redist", "ucrt", "DLLs", "x64")),
        ]
    else:
        paths = []
    return Analysis(
        ["gridsync/cli.py"],
        pathex=paths,
        binaries=None,
        datas=[
            ("gridsync/resources/*", "resources"),
            ("gridsync/resources/providers/*", "resources/providers"),
        ],
        hiddenimports=[
	    "cffi",
	    "PyQt5.sip",
	    # Required for charset-normalizer 3.0.1. To be fixed by a future
	    # version of pyinstaller-hooks-contrib. See/follow:
	    # https://github.com/pyinstaller/pyinstaller-hooks-contrib/issues/534
	    "charset_normalizer.md__mypyc",
	],
        hookspath=["pyinstaller-hooks"],
        runtime_hooks=[],
        excludes=["FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"],
        win_no_prefer_redirects=False,
        win_private_assemblies=False,
        cipher=None,
    )


def build_tahoe(analysis):
    exe = EXE(
        PYZ(analysis.pure, analysis.zipped_data, cipher=None),
        analysis.scripts,
        [("u", None, "OPTION")],  # Enable unbuffered stdio
        exclude_binaries=True,
        name="tahoe",
        debug=False,
        strip=False,
        upx=False,
        console=True,
    )
    return [exe, analysis.binaries, analysis.zipfiles, analysis.datas]


def build_magic_folder(analysis):
    exe = EXE(
        PYZ(analysis.pure, analysis.zipped_data, cipher=None),
        analysis.scripts,
        [("u", None, "OPTION")],  # Enable unbuffered stdio
        exclude_binaries=True,
        name="magic-folder",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True,
    )
    return [exe, analysis.binaries, analysis.zipfiles, analysis.datas]


def build_gridsync(analysis):
    exe = EXE(
        PYZ(analysis.pure, analysis.zipped_data, cipher=None),
        analysis.scripts,
        exclude_binaries=True,
        name=app_name,
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon=str(Path(settings["build"]["win_icon"]).resolve()),
    )
    return [exe, analysis.binaries, analysis.zipfiles, analysis.datas]


def bundle_tahoe(files):
    COLLECT(*files, strip=False, upx=False, name="Tahoe-LAFS")


def bundle_magic_folder(files):
    COLLECT(*files, strip=False, upx=False, name="magic-folder")


def bundle_gridsync(files):
    mac_background_only = settings["build"].get("mac_background_only", False)
    if mac_background_only and mac_background_only.lower() != "false":
        mac_background_only = True
    from gridsync import __version__ as version

    BUNDLE(
        COLLECT(*files, strip=False, upx=False, name=app_name),
        name=(app_name + ".app"),
        icon=str(Path(settings["build"]["mac_icon"]).resolve()),
        bundle_identifier=settings["build"]["mac_bundle_identifier"],
        info_plist={
            "CFBundleShortVersionString": version,
            "LSBackgroundOnly": mac_background_only,
            "LSUIElement": mac_background_only,
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
        },
    )


def finalize_gridsync_bundle():
    if sys.platform == "darwin":
        dist = Path("dist", f"{app_name}.app", "Contents", "MacOS")
    else:
        dist = Path("dist", app_name)

    for bundle in ("Tahoe-LAFS", "magic-folder"):
        bundle_path = Path("dist", bundle)
        if bundle_path.exists() and bundle_path.is_dir():
            dst = Path(dist, bundle)
            print(f"Copying {bundle_path} to {dst}...")
            shutil.copytree(bundle_path, dst)

    paths_to_move = []
    # Prepend app_name to avoid confusion regarding process names/ownership.
    # See https://github.com/gridsync/gridsync/issues/422
    tahoe_exe = "tahoe.exe" if sys.platform == "win32" else "tahoe"
    paths_to_move.append(
        (
            Path(dist, "Tahoe-LAFS", tahoe_exe),
            Path(dist, "Tahoe-LAFS", f"{app_name}-{tahoe_exe}"),
        )
    )
    paths_to_move.append(
        (Path(dist, tahoe_exe), Path(dist, f"{app_name}-{tahoe_exe}"))
    )
    magic_folder_exe = (
        "magic-folder.exe" if sys.platform == "win32" else "magic-folder"
    )
    paths_to_move.append(
        (
            Path(dist, "magic-folder", magic_folder_exe),
            Path(dist, "magic-folder", f"{app_name}-{magic_folder_exe}"),
        )
    )
    paths_to_move.append(
        (
            Path(dist, magic_folder_exe),
            Path(dist, f"{app_name}-{magic_folder_exe}"),
        )
    )
    # XXX Sometimes .json files from `gridsync/resources/providers/` end up
    # in `gridsync/resources/`. I'm not sure why PyInstaller does this.. :/
    for p in Path(dist, "resources").glob("*-*.json"):
        paths_to_move.append((p, Path(dist, "resources", "providers", p.name)))
    if sys.platform not in ("darwin", "win32"):
        paths_to_move.append(
            (Path(dist, app_name), Path(dist, app_name.lower()))
        )
    for src, dst in paths_to_move:
        if src.exists() and src.is_file():
            print(f"Moving {src} to {dst}...")
            shutil.move(src, dst)

    paths_to_remove = []
    if sys.platform != "win32":
        # The script used to generate an Inno Setup installer configuration
        # currently loads the version from `gridsync/resources/version.txt`
        # so don't delete it on Windows; see `scripts/make_installer.py`
        paths_to_remove.append(gridsync_version_file)
    # The presence of *.dist-info/RECORD files causes issues with reproducible
    # builds; see: https://github.com/gridsync/gridsync/issues/363
    paths_to_remove.extend([p for p in dist.glob("**/*.dist-info/RECORD")])
    if sys.platform not in ("darwin", "win32"):
        bad_libs = [
            "libX11.so.6",  # https://github.com/gridsync/gridsync/issues/43
            "libdrm.so.2",  # https://github.com/gridsync/gridsync/issues/47
            "libstdc++.so.6",  # https://github.com/gridsync/gridsync/issues/189
            "libpango-1.0.so.0",  # https://github.com/gridsync/gridsync/issues/487
            "libpangocairo-1.0.so.0",
            "libpangoft2-1.0.so.0",
        ]
        for lib in bad_libs:
            paths_to_remove.append(Path(dist, lib))
    for path in paths_to_remove:
        if path.exists():
            print(f"Removing {path}...")
            path.unlink()


results = []
# Insertion order matters, for the purposes of the 'MERGE' step below;
# the Gridsync package needs to be the first in the list here. See:
# https://pyinstaller.readthedocs.io/en/stable/spec-files.html#multipackage-bundles
if gridsync_available:
    gridsync_analysis = analyze_gridsync()
    results.append((gridsync_analysis, app_name, app_name))
if tahoe_available:
    tahoe_analysis = analyze_tahoe()
    results.append((tahoe_analysis, "tahoe", "tahoe"))
if magic_folder_available:
    magic_folder_analysis = analyze_magic_folder()
    results.append((magic_folder_analysis, "magic-folder", "magic-folder"))
if len(results) > 1:
    MERGE(*results)

if gridsync_available:
    gridsync_files = build_gridsync(gridsync_analysis)
if tahoe_available:
    tahoe_files = build_tahoe(tahoe_analysis)
    if gridsync_available:
        gridsync_files.extend(tahoe_files)
    else:
        bundle_tahoe(tahoe_files)
if magic_folder_available:
    magic_folder_files = build_magic_folder(magic_folder_analysis)
    if gridsync_available:
        gridsync_files.extend(magic_folder_files)
    else:
        bundle_magic_folder(magic_folder_files)
if gridsync_available:
    bundle_gridsync(gridsync_files)
    finalize_gridsync_bundle()
