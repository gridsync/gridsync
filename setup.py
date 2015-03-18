#!/usr/bin/env python2

from setuptools import setup, find_packages

setup(
    name = "gridsync",
    version = "0.0.1",
    packages = find_packages(),
    scripts = ['gridsync/scripts/gridsync'],
    install_requires = ['allmydata-tahoe', 'watchdog', 'wxPython'],
)
