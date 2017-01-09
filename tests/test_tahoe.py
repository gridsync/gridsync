# -*- coding: utf-8 -*-

import os

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
