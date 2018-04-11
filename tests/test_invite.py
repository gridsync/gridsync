# -*- coding: utf-8 -*-

import os

from gridsync.invite import get_settings_from_cheatcode, is_valid


def test_invalid_code_not_three_words():
    assert not is_valid('topmost-vagabond')


def test_invalid_code_first_word_not_digit():
    assert not is_valid('corporate-cowbell-commando')


def test_invalid_code_second_word_not_in_wordlist():
    assert not is_valid('2-tanooki-travesty')


def test_invalid_code_third_word_not_in_wordlist():
    assert not is_valid('3-eating-wasabi')


def test_valid_code_is_valid():
    assert is_valid('1-cranky-tapeworm')


def test_get_settings_from_cheatcode(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir')
    providers_path = os.path.join(pkgdir, 'resources', 'providers')
    os.makedirs(providers_path)
    with open(os.path.join(providers_path, 'test-test.json'), 'w') as f:
        f.write('{"introducer": "pb://"}')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    settings = get_settings_from_cheatcode('test-test')
    assert settings['introducer'] == 'pb://'


def test_get_settings_from_cheatcode_none(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir-empty')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    assert get_settings_from_cheatcode('test-test') is None
