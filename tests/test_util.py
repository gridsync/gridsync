# -*- coding: utf-8 -*-

import pytest

from gridsync.util import humanized_list, dehumanized_size


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


def test_dehumanize_none_is_0():
    assert dehumanized_size(None) == 0


def test_dehumanize_32B():
    assert dehumanized_size('32 Bytes') == 32


def test_dehumanize_1KB():
    assert dehumanized_size('1KB') == 1024


def test_dehumanize_256GB():
    assert dehumanized_size('256GB') == 274877906944


def test_dehumanize_value_error_prefix_not_digit():
    with pytest.raises(ValueError):
        assert dehumanized_size('two bytes') == 2


def test_dehumanize_value_error_unknown_suffix():
    with pytest.raises(ValueError):
        assert dehumanized_size('3 ninjas') == 3
