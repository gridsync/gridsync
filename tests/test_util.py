# -*- coding: utf-8 -*-

from binascii import hexlify, unhexlify

import pytest

from gridsync.util import (
    b58decode,
    b58encode,
    future_date,
    humanized_list,
    strip_html_tags,
    to_bool,
    traceback,
)

# From https://github.com/bitcoin/bitcoin/blob/master/src/test/data/base58_encode_decode.json
base58_test_pairs = [
    ["", ""],
    ["61", "2g"],
    ["626262", "a3gV"],
    ["636363", "aPEr"],
    [
        "73696d706c792061206c6f6e6720737472696e67",
        "2cFupjhnEsSn59qHXstmK2ffpLv2",
    ],
    [
        "00eb15231dfceb60925886b67d065299925915aeb172c06647",
        "1NS17iag9jJgTHD1VXjvLCEnZuQ3rJDE9L",
    ],
    ["516b6fcd0f", "ABnLTmg"],
    ["bf4f89001e670274dd", "3SEo3LWLoPntC"],
    ["572e4794", "3EFU7m"],
    ["ecac89cad93923c02321", "EJDM8drfXA6uyA"],
    ["10c8511e", "Rt5zm"],
    ["00000000000000000000", "1111111111"],
]


@pytest.mark.parametrize("b,encoded", base58_test_pairs)
def test_b58encode(b, encoded):
    assert b58encode(unhexlify(b.encode())) == encoded


@pytest.mark.parametrize("decoded,s", base58_test_pairs)
def test_b58decode(decoded, s):
    assert hexlify(b58decode(s)).decode() == decoded


def test_b58decode_value_error():
    with pytest.raises(ValueError):
        b58decode("abcl23")


@pytest.mark.parametrize(
    "s, result",
    [
        ("True", True),
        ("False", False),
        ("FaLsE", False),
        ("f", False),
        ("t", True),
        ("No", False),
        ("Yes", True),
        ("N", False),
        ("Y", True),
        ("off", False),
        ("on", True),
        ("None", False),
        ("0", False),
        ("1", True),
        ("", False),
        ("X", True),
    ],
)
def test_to_bool(s, result):
    assert to_bool(s) == result


@pytest.mark.parametrize(
    "items,kind,humanized",
    [
        [None, None, None],
        [["Alice"], None, "Alice"],
        [["Alice", "Bob"], None, "Alice and Bob"],
        [["Alice", "Bob", "Eve"], None, "Alice, Bob, and Eve"],
        [
            ["Alice", "Bob", "Eve", "Mallory"],
            "characters",
            "Alice, Bob, and 2 other characters",
        ],
    ],
)
def test_humanized_list(items, kind, humanized):
    assert humanized_list(items, kind) == humanized


def test_future_date_returns_centuries_for_large_int_days():
    assert future_date(2**32) == "Centuries"


def test_future_date_does_not_return_centuries_for_small_int_days():
    assert future_date(365 * 5) != "Centuries"


@pytest.mark.parametrize(
    "s,expected",
    [
        ["1<p>2<br>3", "123"],
        ['<a href="https://example.org">link</a>', "link"],
    ],
)
def test_strip_html_tags(s, expected):
    assert strip_html_tags(s) == expected


def test_traceback():
    try:
        raise ValueError("test")
    except ValueError as exc:
        tb = traceback(exc)
    assert isinstance(tb, str)
    assert "ValueError: test" in tb
