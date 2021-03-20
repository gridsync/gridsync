from typing import Generator, TypeVar

A = TypeVar("A")

TwistedDeferred = Generator[int, None, A]
