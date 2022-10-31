# -*- coding: utf-8 -*-

import pytest

from gridsync.voucher import (
    dehyphenate,
    generate_code,
    generate_pair,
    generate_voucher,
    get_checksum,
    hyphenate,
    is_valid,
)


@pytest.mark.parametrize(
    "code,expected",
    [
        [b"AAAAAAAA", "QN_NCTiQJ0OOmRTZZ0sydpl_e_AK7R_KuwUtJAS5EQal"],
        [b"BBBBBBBB", "_g_kB_grSW-JComZ8pXdFQS6Q7fXwFd70s0khdesQUy6"],
        [b"CCCCCCCC", "Px4cpOVRJ3quleEpWBspQfPrz14wrq0Wkd5xggyTnkzE"],
        [b"DDDDDDDD", "LNtbnSsfAQHrwqDXBy5eYcc9TiR60deO4AwNCwn8et-D"],
    ],
)
def test_generate_voucher(code, expected):
    assert generate_voucher(code) == expected


def test_generate_voucher_with_random_data():
    assert len(generate_voucher()) == 44


@pytest.mark.parametrize(
    "s,expected",
    [
        ["ABCDEFGHIJKLMNOP", "ABCD-EFGH-IJKL-MNOP"],
        ["ABCDEFGHIJKLMN", "ABCD-EFGH-IJKL-MN"],
        ["ABCDEFGHIJKL", "ABCD-EFGH-IJKL"],
        ["ABCD", "ABCD"],
        ["", ""],
    ],
)
def test_hyphenate(s, expected):
    assert hyphenate(s) == expected


@pytest.mark.parametrize(
    "s,expected",
    [
        ["ABCD-EFGH-IJKL-MNOP", "ABCDEFGHIJKLMNOP"],
        ["ABCD-EFGH-IJKL-MN", "ABCDEFGHIJKLMN"],
        ["ABCD-EFGH-IJKL", "ABCDEFGHIJKL"],
        ["ABCD", "ABCD"],
        ["", ""],
    ],
)
def test_dehyphenate(s, expected):
    assert dehyphenate(s) == expected


def test_get_checksum():
    assert get_checksum(b"AAAAAAAA") == b";b"


def test_generate_code():
    assert len(generate_code()) == 16


@pytest.mark.parametrize(
    "code,expected",
    [
        ["GEZDGNBVGY3TQX2V", True],
        ["GEZD-GNBV-GY3T-QX2V", True],
        ["GEZDGNBVGY3TQX21", False],  # "1" is not in base32 alphabet
        ["GEZDGNBVGY3TQX22", False],  # Checksum fails
        ["AAAA-AAAA-AAAA-AAAŁ", False],  # Non-ASCII character
    ],
)
def test_is_valid(code, expected):
    assert is_valid(code) == expected


def test_generate_pair_returns_valid_code():
    code, _ = generate_pair()
    assert is_valid(code) is True


def test_generate_pair_derives_string_from_code():
    code, string = generate_pair()
    assert generate_voucher(dehyphenate(code).encode()) == string
