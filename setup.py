#!/usr/bin/env python

import re
import struct
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    user_options = [('tox-args=', 'a', "Arguments to pass to tox")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.tox_args = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox
        import shlex
        args = self.tox_args
        if args:
            args = shlex.split(self.tox_args)
        errno = tox.cmdline(args=args)
        sys.exit(errno)


requirements = [
    'humanize',
    'magic-wormhole',
    'pyyaml',
    'qt5reactor',
    'treq',
    'twisted[tls]',
]

if sys.platform.startswith('linux'):
    requirements.append('txdbus')

# Other versions/platforms will need to install PyQt5 separately,
# as PyPI wheels are only made available for 3.5+ on Linux/Mac/Win
python_version = (sys.version_info.major, sys.version_info.minor)
if python_version >= (3, 5) and sys.platform in ('linux', 'darwin', 'win32'):
    requirements.append('pyqt5')

    # PyQt5 wheels are not available for 32-bit Linux;
    # see https://github.com/gridsync/gridsync/issues/45
    if sys.platform == 'linux' and (struct.calcsize('P') * 8) == 32:
        try:
            import PyQt5  # noqa; F401 (imported but unused)
        except ImportError:
            sys.exit(
                "PyQt5 wheels are not available on this platform. Please "
                "manually install PyQt5 into this environment and try again.")
        requirements.remove('pyqt5')


if python_version < (3, 2):
    requirements.append('configparser')


module_file = open("gridsync/__init__.py").read()
metadata = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", module_file))

version_file = open("gridsync/_version.py").read()
version = re.findall("__version__\s*=\s*'([^']+)'", version_file)[0]


setup(
    name="gridsync",
    version=version,
    description="Synchronize local directories with Tahoe-LAFS storage grids.",
    long_description=open('README.rst').read(),
    author=metadata["author"],
    url=metadata["url"],
    license=metadata["license"],
    keywords="gridsync tahoe-lafs tahoe lafs allmydata-tahoe",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Environment :: MacOS X",
        "Environment :: Win32 (MS Windows)",
        "Environment :: X11 Applications",
        "Environment :: X11 Applications :: Gnome",
        "Environment :: X11 Applications :: GTK",
        "Environment :: X11 Applications :: KDE",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "License :: DFSG approved",
        "License :: OSI Approved",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: Windows 7",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Topic :: Communications :: File Sharing",
        "Topic :: Desktop Environment",
        "Topic :: Internet",
        "Topic :: Security",
        "Topic :: System :: Archiving",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Archiving :: Mirroring",
        "Topic :: System :: Clustering",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Filesystems",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    packages=['gridsync', 'gridsync.gui'],
    package_data={
        'gridsync': ['resources/*']
    },
    entry_points={
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires=requirements,
    test_suite="tests",
    tests_require=['tox'],
    cmdclass={'test': Tox},
)
