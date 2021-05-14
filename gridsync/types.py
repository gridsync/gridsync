# mypy: allow-any-explicit
from typing import Any, Generator, TypeVar

from treq.response import _Response

A = TypeVar("A")

TreqResponse = _Response

# This can probably be removed with the next Twisted release (after
# 21.2.0), since type hints have been aded for twisted.internet.defer:
# https://github.com/twisted/twisted/pull/1448
TwistedDeferred = Generator[int, Any, A]
