#!/usr/bin/env python3

from configparser import RawConfigParser
import re
import struct
import sys

from setuptools import setup


if (sys.version_info.major, sys.version_info.minor) < (3, 5):
    sys.exit(
        "This version of Python ({}.{}) is no longer supported by Gridsync; "
        "please upgrade to Python 3.5 or higher and try again".format(
            sys.version_info.major, sys.version_info.minor))


requirements = [
    'humanize',
    'magic-wormhole',
    'PyNaCl >= 1.2.0',  # 1.2.0 adds Argon2id KDF
    'PyQt5',
    'pyyaml',
    'qt5reactor',
    'treq',
    'twisted[tls]',
    'txtorcon',
    'zxcvbn',
]

if sys.platform.startswith('linux') and (struct.calcsize('P') * 8) == 32:
    try:
        import PyQt5  # noqa; F401 (imported but unused)
    except ImportError:
        sys.exit(
            "PyQt5 wheels are not available for 32-bit GNU/Linux. Please "
            "manually install PyQt5 into this environment and try again.")
    requirements.remove('PyQt5')


module_file = open("gridsync/__init__.py").read()
metadata = dict(re.findall(r"__([a-z]+)__\s*=\s*'([^']+)'", module_file))

version_file = open("gridsync/_version.py").read()
version = re.findall(r"__version__\s*=\s*'([^']+)'", version_file)[0]


if sys.platform == 'darwin':
    config = RawConfigParser()
    config.read('gridsync/resources/config.txt')
    app_name = config.get('application', 'name')
    build_settings = {}
    for option, value in config.items('build'):
        build_settings[option] = value
    extra_options = {
        'setup_requires': ['py2app'],
        'app': ['gridsync/cli.py'],
        'options': {'py2app': {
            'argv_emulation': True,
            'iconfile': build_settings['mac_icon'],
            'includes': ['cffi'],
            'plist': {
                'CFBundleDisplayName': app_name,
                'CFBundleExecutable': app_name,
                'CFBundleIdentifier': build_settings['mac_bundle_identifier'],
                'CFBundleName': app_name,
                'LSBackgroundOnly': True,
                'LSUIElement': True
            }
        }}
    }
else:
    extra_options = {}


setup(
    name="gridsync",
    version=version,
    description="Synchronize local directories with Tahoe-LAFS storage grids.",
    long_description=open('README.rst').read(),
    author=metadata["author"],
    url=metadata["url"],
    license=metadata["license"],
    keywords="gridsync tahoe-lafs tahoe lafs allmydata-tahoe magic-wormhole",
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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
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
    packages=['gridsync', 'gridsync.gui'],
    package_data={
        'gridsync': ['resources/*', 'resources/providers/*']
    },
    entry_points={
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires=requirements,
    **extra_options
)
