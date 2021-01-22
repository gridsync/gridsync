#!/usr/bin/env python3

import base64
import hashlib
import os

from typing import Optional


def generate_voucher(data: Optional[bytes] = b"") -> str:
    if not data:
        data = os.urandom(64)
    digest = hashlib.blake2b(data, digest_size=33).digest()
    # XXX Truncate after hashing?
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def dashify(s):
    return "-".join([s[i : i + 4] for i in range(0, len(s), 4)])


if __name__ == "__main__":
    for _ in range(100):
        b = base64.b32encode(os.urandom(10))
        print("{} -> {}".format(dashify(b.decode()), generate_voucher(b)))

# TODO:
# Append checksum chars to human/user-facing code?
# Use different alphabet with fewer ambiguous chars?
