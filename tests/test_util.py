# -*- coding: utf-8 -*-

from gridsync.util import humanized_list


def test_humanized_list_Alice():
    result = humanized_list(['Alice'])
    assert result == 'Alice'


def test_humanized_list_Alice_Bob():
    result = humanized_list(['Alice', 'Bob'])
    assert result == 'Alice and Bob'


def test_humanized_list_Alice_Bob_Eve():
    result = humanized_list(['Alice', 'Bob', 'Eve'])
    assert result == 'Alice, Bob, and Eve'


def test_humanized_list_Alice_Bob_Eve_Mallory():
    result = humanized_list(['Alice', 'Bob', 'Eve', 'Mallory'], 'characters')
    assert result == 'Alice, Bob, and 2 other characters'
