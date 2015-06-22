#!/usr/bin/env python2

from setuptools import setup, find_packages


def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name="gridsync",
    version="0.0.1",
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
    packages=find_packages(exclude=("tests", "docs")),
    entry_points={
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires=['allmydata-tahoe', 'watchdog', 'qt4reactor'],
    test_suite="tests"
)
