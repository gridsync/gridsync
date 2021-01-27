#!/usr/bin/env python3

import base64
import binascii
import hashlib
import os
from typing import Optional


def generate_voucher(data: Optional[bytes] = b"") -> str:
    if not data:
        data = os.urandom(64)
    digest = hashlib.blake2b(data, digest_size=33).digest()
    # XXX Truncate after hashing?
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def hyphenate(s: str) -> str:
    return "-".join([s[i : i + 4] for i in range(0, len(s), 4)])


def dehyphenate(s: str) -> str:
    return s.replace("-", "")


def get_checksum(b: bytes, length: int = 2) -> bytes:
    return hashlib.blake2b(b, digest_size=length).digest()


def generate_code() -> bytes:
    b = os.urandom(8)
    checksum = get_checksum(b)
    return base64.b32encode(b + checksum)


def is_valid(code: str, checksum_length: int = 2) -> bool:
    code = dehyphenate(code)
    try:
        decoded = base64.b32decode(code)
    except binascii.Error:
        return False
    b = decoded[:-checksum_length]
    checksum = decoded[-checksum_length:]
    if checksum == get_checksum(b):
        return True
    return False


if __name__ == "__main__":
    for _ in range(100):
        code = generate_code()
        print(
            "{} -> {}".format(hyphenate(code.decode()), generate_voucher(code))
        )

# TODO:
# Use different alphabet with fewer ambiguous chars?
