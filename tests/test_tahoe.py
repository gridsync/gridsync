# -*- coding: utf-8 -*-

import difflib
import os
import sys
if sys.version_info >= (3, 4):
    from importlib import reload

import pytest

import gridsync.tahoe


@pytest.fixture(scope='module')
def tahoe(tmpdir_factory):
    config = '[node]\nnickname = default'
    tahoe = gridsync.tahoe.Tahoe(str(tmpdir_factory.mktemp('tahoe')))
    with open(os.path.join(tahoe.nodedir, 'tahoe.cfg'), 'w') as f:
        f.write(config)
    return tahoe


def test_config_get(tahoe):
    assert tahoe.config_get('node', 'nickname') == 'default'


def test_config_set(tahoe):
    tahoe.config_set('node', 'nickname', 'test')
    assert tahoe.config_get('node', 'nickname') == 'test'


def test_append_tahoe_bundle_to_PATH(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    old_path = os.environ['PATH']
    reload(gridsync.tahoe)
    delta = ''
    for _, s in enumerate(difflib.ndiff(old_path, os.environ['PATH'])):
        if s[0] == '+':
            delta += s[-1]
    assert delta == os.pathsep + os.path.join(os.path.dirname(sys.executable),
                                              'Tahoe-LAFS')
