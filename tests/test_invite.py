# -*- coding: utf-8 -*-

from gridsync.gui.invite import is_valid, InviteForm


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


def test_init_invite_form():
    invite_form = InviteForm(None)
    assert invite_form
