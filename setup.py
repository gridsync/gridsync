#!/usr/bin/env python2

import os
import re
import sys

from setuptools import setup, find_packages, Command


class PyTest(Command):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        self.pytest_args = []

    def finalize_options(self):
        pass

    def run(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)

#class PyTest(TestCommand):
#    def finalize_options(self):
#        TestCommand.finalize_options(self)
#        self.test_args = []
#        self.test_suite = True

#    def run_tests(self):
#        import pytest
#        errcode = pytest.main(self.test_args)
#        sys.exit(errcode)


requirements = ['allmydata-tahoe', 'watchdog', 'qt4reactor']
if sys.platform == 'linux2':
    requirements.append('notify2')

execfile("gridsync/_version.py")

module_file = open("gridsync/__init__.py").read()
metadata = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", module_file))

setup(
    name="gridsync",
    version=__version__,
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
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Unix",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
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
    packages=["gridsync", "gridsync.forms"],
    entry_points={
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires=requirements,
    test_suite="tests",
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
)
