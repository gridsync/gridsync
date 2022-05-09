"""Synchronize local directories with Tahoe-LAFS storage grids."""

import json
import os
import sys
from collections import namedtuple
from pathlib import Path
from typing import Optional

from qtpy import API_NAME, PYQT_VERSION, PYSIDE_VERSION, QT_VERSION

from gridsync._version import get_versions  # type: ignore
from gridsync.config import Config
from gridsync.util import to_bool

__author__ = "Christopher R. Wood"
__url__ = "https://github.com/gridsync/gridsync"
__license__ = "GPLv3"


if sys.platform in ("win32", "darwin"):
    import certifi

    # Workaround for broken-by-default certificate verification on Windows.
    # See https://github.com/twisted/treq/issues/94#issuecomment-116226820
    # TLS certificate verification was also observed to be broken on macOS
    # 10.16 <https://github.com/gridsync/gridsync/issues/459> -- and using
    # `certifi`'s CA bundle reportedly fixed it.
    os.environ["SSL_CERT_FILE"] = certifi.where()


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


for envvar, value in os.environ.items():
    if envvar.startswith("GRIDSYNC_"):
        words = envvar.split("_")
        if len(words) >= 3:
            section = words[1].lower()
            option = "_".join(words[2:]).lower()
            try:
                settings[section][option] = value
            except KeyError:
                settings[section] = {option: value}

try:
    APP_NAME = settings["application"]["name"]
except KeyError:
    APP_NAME = "Gridsync"

DEFAULT_AUTOSTART = to_bool(settings.get("defaults", {}).get("autostart", ""))


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


def resource(filename: str) -> str:
    return os.path.join(pkgdir, "resources", filename)


cheatcodes = []
try:
    for file in os.listdir(os.path.join(pkgdir, "resources", "providers")):
        cheatcodes.append(file.split(".")[0].lower())
except OSError:
    pass


def load_settings_from_cheatcode(cheatcode: str) -> Optional[dict]:
    path = os.path.join(pkgdir, "resources", "providers", cheatcode + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.loads(f.read())
    except (OSError, json.decoder.JSONDecodeError):
        return None


def cheatcode_used(cheatcode: str) -> bool:
    s = load_settings_from_cheatcode(cheatcode)
    if not s:
        return False
    return Path(config_dir, s.get("nickname", ""), "tahoe.cfg").exists()


CONNECTION_DEFAULT = settings.get("connection", {}).get("default", "")
_default_settings = load_settings_from_cheatcode(CONNECTION_DEFAULT)
if _default_settings:
    CONNECTION_DEFAULT_NICKNAME = _default_settings.get("nickname", "")
else:
    CONNECTION_DEFAULT_NICKNAME = ""


if API_NAME.lower().startswith("pyqt"):
    QT_API_VERSION = f"{API_NAME}-{PYQT_VERSION}"
else:
    QT_API_VERSION = f"{API_NAME}-{PYSIDE_VERSION}"
QT_LIB_VERSION = QT_VERSION or ""


# When running frozen, Versioneer returns a version string of "0+unknown"
# due to the application (typically) being executed out of the source tree
# so load the version string from a file written at freeze-time instead.
def get_version() -> str:
    if getattr(sys, "frozen", False):
        try:
            with open(resource("version.txt"), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return "Unknown"
    else:
        return get_versions()["version"]


__version__ = get_version()
