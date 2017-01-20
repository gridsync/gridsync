# -*- coding: utf-8 -*-

import os

import pytest

from gridsync.tahoe import is_valid_furl, Tahoe


@pytest.fixture(scope='module')
def tahoe(tmpdir_factory):
    config = '[node]\nnickname = default'
    tahoe = Tahoe(str(tmpdir_factory.mktemp('tahoe')))
    with open(os.path.join(tahoe.nodedir, 'tahoe.cfg'), 'w') as f:
        f.write(config)
    return tahoe


def test_is_valid_furl():
    assert is_valid_furl('pb://abc234@example.org:12345/introducer') == True


def test_is_valid_furl_no_port():
    assert is_valid_furl('pb://abc234@example.org/introducer') == False


def test_is_valid_furl_no_host_separator():
    assert is_valid_furl('pb://abc234example.org:12345/introducer') == False


def test_is_valid_furl_invalid_char_in_connection_hint():
    assert is_valid_furl('pb://abc234@exam/ple.org:12345/introducer') == False


def test_is_valid_furl_tub_id_not_base32():
    assert is_valid_furl('pb://abc123@example.org:12345/introducer') == False


def test_config_get(tahoe):
    assert tahoe.config_get('node', 'nickname') == 'default'


def test_config_set(tahoe):
    tahoe.config_set('node', 'nickname', 'test')
    assert tahoe.config_get('node', 'nickname') == 'test'
