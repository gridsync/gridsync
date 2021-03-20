from typing import Generator, TypeVar

from treq.response import _Response

A = TypeVar("A")

TreqResponse = _Response

TwistedDeferred = Generator[int, None, A]
