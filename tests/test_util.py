# -*- coding: utf-8 -*-

from gridsync.util import h2b, b2h, humanized_list


def test_1B_2b():
    assert h2b('1B') == 1


def test_1024B_2b():
    assert h2b('1KB') == 1024


def test_256GB_2b():
    assert h2b('256GB') == 274877906944


def test_274877906944_2h():
    assert b2h(274877906944) == '256.0 GB'


def test_1024_2h():
    assert b2h(1024) == '1.0 KB'


def test_1_2h():
    assert b2h(1) == '1.0 B'


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
