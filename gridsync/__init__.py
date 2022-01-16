"""Synchronize local directories with Tahoe-LAFS storage grids."""

import os
import sys
from collections import namedtuple

from gridsync._version import get_versions  # type: ignore
from gridsync.config import Config

__author__ = "Christopher R. Wood"
__url__ = "https://github.com/gridsync/gridsync"
__license__ = "GPLv3"


if getattr(sys, "frozen", False):
    pkgdir = os.path.dirname(os.path.realpath(sys.executable))
    os.environ["PATH"] += os.pathsep + pkgdir
    os.environ["PATH"] += os.pathsep + os.path.join(pkgdir, "Tahoe-LAFS")
    os.environ["PATH"] += os.pathsep + os.path.join(pkgdir, "magic-folder")
    if sys.platform == "win32":
        # Workaround for PyInstaller being unable to find Qt5Core.dll on PATH.
        # See https://github.com/pyinstaller/pyinstaller/issues/4293
        _meipass = getattr(sys, "_MEIPASS", "")
        if _meipass:
            os.environ["PATH"] = _meipass + os.pathsep + os.environ["PATH"]
    try:
        del sys.modules["twisted.internet.reactor"]  # PyInstaller workaround
    except KeyError:
        pass
    if sys.platform not in ("win32", "darwin"):
        # PyInstaller's bootloader sets the 'LD_LIBRARY_PATH' environment
        # variable to the root of the executable's directory which causes
        # `xdg-open` -- and, by extension, QDesktopServices.openUrl() -- to
        # fail to properly locate/launch applications by MIME-type/URI-handler.
        # Unsetting it globally here fixes this issue.
        os.environ.pop("LD_LIBRARY_PATH", None)
else:
    pkgdir = os.path.dirname(os.path.realpath(__file__))


settings = Config(os.path.join(pkgdir, "resources", "config.txt")).load()

try:
    APP_NAME = settings["application"]["name"]
except KeyError:
    APP_NAME = "Gridsync"


grid_invites_enabled: bool = True
invites_enabled: bool = True
multiple_grids_enabled: bool = True
tor_enabled: bool = True

_features = settings.get("features")
if _features:
    _grid_invites = _features.get("grid_invites")
    if _grid_invites and _grid_invites.lower() == "false":
        grid_invites_enabled = False
    _invites = _features.get("invites")
    if _invites and _invites.lower() == "false":
        invites_enabled = False
    _multiple_grids = _features.get("multiple_grids")
    if _multiple_grids and _multiple_grids.lower() == "false":
        multiple_grids_enabled = False
    _tor = _features.get("tor")
    if _tor and _tor.lower() == "false":
        tor_enabled = False

Features = namedtuple("Features", "grid_invites invites multiple_grids tor")
features = Features(
    grid_invites_enabled, invites_enabled, multiple_grids_enabled, tor_enabled
)


if sys.platform == "win32":
    appdata = str(os.getenv("APPDATA"))
    config_dir = os.path.join(appdata, APP_NAME)
    autostart_file_path = os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
        APP_NAME + ".lnk",
    )
elif sys.platform == "darwin":
    config_dir = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", APP_NAME
    )
    autostart_file_path = os.path.join(
        os.path.expanduser("~"), "Library", "LaunchAgents", APP_NAME + ".plist"
    )
    # Required for macOS 11 ("Big Sur") compatibility.
    # See https://github.com/gridsync/gridsync/issues/319
    os.environ["QT_MAC_WANTS_LAYER"] = "1"
else:
    config_home = os.environ.get(
        "XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config")
    )
    config_dir = os.path.join(config_home, APP_NAME.lower())
    autostart_file_path = os.path.join(
        config_home, "autostart", APP_NAME + ".desktop"
    )


def resource(filename):
    return os.path.join(pkgdir, "resources", filename)


# When running frozen, Versioneer returns a version string of "0+unknown"
# due to the application (typically) being executed out of the source tree
# so load the version string from a file written at freeze-time instead.
if getattr(sys, "frozen", False):
    try:
        with open(resource("version.txt"), encoding="utf-8") as f:
            __version__ = f.read()
    except OSError:
        __version__ = "Unknown"
else:
    __version__ = get_versions()["version"]
