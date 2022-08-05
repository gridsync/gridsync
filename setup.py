#!/usr/bin/env python3
import os
import re
import struct
import sys

from setuptools import setup

import versioneer

# These requirements are also declared via requirements/gridsync.in. Please
# ensure that changes made to this list are propagated there (and vice versa).
requirements = [
    "atomicwrites",
    "attrs",
    # These autobahn constraints are inherited from ZKAPAuthorizer e1debb6
    # and can probably go away once autobahn provides a release containing
    # https://github.com/crossbario/autobahn-python/pull/1578
    "autobahn >= 21.11.1, != 22.5.1, != 22.4.2, != 22.4.1",
    'certifi ; sys_platform == "win32"',
    'distro ; sys_platform != "darwin" and sys_platform != "win32"',
    "humanize",
    "hyperlink",
    "magic-wormhole",
    "psutil",
    "PyNaCl >= 1.2.0",  # 1.2.0 adds Argon2id KDF
    "pyyaml",
    "qtpy",
    "tahoe-lafs",
    "treq",
    "twisted[tls] >= 21.7.0",  # 21.7.0 adds Deferred type hinting/annotations
    "txdbus ; sys_platform != 'darwin' and sys_platform != 'win32'",
    "txtorcon",
    "watchdog",
    "zxcvbn",
]
qt_requirements = {
    "pyqt5": ["PyQt5", "PyQtChart"],
    "pyqt6": ["PyQt6", "PyQt6-Charts"],
    "pyside2": ["PySide2"],
    "pyside6": ["PySide6"],
}
qt_api = os.environ.get("QT_API", "pyqt5").lower()
if qt_api not in qt_requirements:
    sys.exit(
        f'The requested Qt API "{qt_api}" is invalid; '
        f'valid QT_API options are: {", ".join(qt_requirements.keys())}'
    )
requirements += qt_requirements[qt_api]


if struct.calcsize("P") * 8 == 32:
    sys.exit("Gridsync is not supported on 32-bit systems.")


module_file = open("gridsync/__init__.py").read()
metadata = dict(re.findall(r"__([a-z]+)__\s*=\s*\"([^\"]+)\"", module_file))


setup(
    name="gridsync",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="Synchronize local directories with Tahoe-LAFS storage grids.",
    long_description=open("README.rst").read(),
    author=metadata["author"],
    url=metadata["url"],
    license=metadata["license"],
    keywords="gridsync tahoe-lafs tahoe lafs allmydata-tahoe magic-wormhole",
    python_requires=">=3.9, <3.11",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Environment :: X11 Applications :: Gnome",
        "Environment :: X11 Applications :: GTK",
        "Environment :: X11 Applications :: KDE",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: End Users/Desktop",
        "License :: DFSG approved",
        "License :: OSI Approved",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 7",
        "Operating System :: Microsoft :: Windows :: Windows 8",
        "Operating System :: Microsoft :: Windows :: Windows 8.1",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Communications :: File Sharing",
        "Topic :: Desktop Environment",
        "Topic :: Internet",
        "Topic :: Security",
        "Topic :: Security :: Cryptography",
        "Topic :: System :: Archiving",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Archiving :: Mirroring",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Filesystems",
        "Topic :: System :: Recovery Tools",
        "Topic :: Utilities",
    ],
    packages=["gridsync", "gridsync.gui"],
    package_data={"gridsync": ["resources/*", "resources/providers/*"]},
    entry_points={"console_scripts": ["gridsync=gridsync.cli:main"]},
    install_requires=requirements,
)
