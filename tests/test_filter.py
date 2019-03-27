# -*- coding: utf-8 -*-

import os
from unittest.mock import Mock

import pytest

from gridsync import pkgdir, config_dir, autostart_file_path
from gridsync.filter import get_filters, apply_filters


def test_get_filters():
    core = Mock()
    core.executable = 'test'
    core.gui.main_window.gateways = []
    assert get_filters(core) == [
        (pkgdir, 'PkgDir'),
        (config_dir, 'ConfigDir'),
        (autostart_file_path, 'AutostartFilePath'),
        (os.path.expanduser('~'), 'HomeDir'),
        (core.executable, 'TahoeExecutablePath')
    ]
