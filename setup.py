#!/usr/bin/env python2

from setuptools import setup, find_packages

setup(
    name = "gridsync",
    version = "0.0.1",
    packages = find_packages(),
    entry_points = {
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires = ['allmydata-tahoe', 'watchdog', 'wxPython'],
)
