#!/usr/bin/env python2

from setuptools import setup, find_packages


def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name="gridsync",
    version="0.0.1",
    packages=find_packages(exclude=("tests", "docs")),
    entry_points={
        'console_scripts': ['gridsync=gridsync.cli:main'],
    },
    install_requires=['allmydata-tahoe', 'watchdog', 'pyqt4'],
    test_suite="tests"
)
