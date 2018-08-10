# -*- coding: utf-8 -*-

from binascii import hexlify, unhexlify

import pytest

from gridsync.util import b58encode, b58decode, humanized_list


# From https://github.com/bitcoin/bitcoin/blob/master/src/test/data/base58_encode_decode.json
base58_test_pairs = [
    ["", ""],
    ["61", "2g"],
    ["626262", "a3gV"],
    ["636363", "aPEr"],
    ["73696d706c792061206c6f6e6720737472696e67", "2cFupjhnEsSn59qHXstmK2ffpLv2"],
    ["00eb15231dfceb60925886b67d065299925915aeb172c06647", "1NS17iag9jJgTHD1VXjvLCEnZuQ3rJDE9L"],
    ["516b6fcd0f", "ABnLTmg"],
    ["bf4f89001e670274dd", "3SEo3LWLoPntC"],
    ["572e4794", "3EFU7m"],
    ["ecac89cad93923c02321", "EJDM8drfXA6uyA"],
    ["10c8511e", "Rt5zm"],
    ["00000000000000000000", "1111111111"]
]


@pytest.mark.parametrize("b,encoded", base58_test_pairs)
def test_b58encode(b, encoded):
    assert b58encode(unhexlify(b.encode())) == encoded


@pytest.mark.parametrize("decoded,s", base58_test_pairs)
def test_b58decode(decoded, s):
    assert hexlify(b58decode(s)).decode() == decoded


def test_b58decode_value_error():
    with pytest.raises(ValueError):
        b58decode('abcl23')


@pytest.mark.parametrize("items,kind,humanized", [
    [None, None, None],
    [['Alice'], None, 'Alice'],
    [['Alice', 'Bob'], None, 'Alice and Bob'],
    [['Alice', 'Bob', 'Eve'], None, 'Alice, Bob, and Eve'],
    [['Alice', 'Bob', 'Eve', 'Mallory'], 'characters', 'Alice, Bob, and 2 other characters']
])
def test_humanized_list(items, kind, humanized):
    assert humanized_list(items, kind) == humanized
