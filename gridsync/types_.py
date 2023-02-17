# mypy: allow-any-explicit
from typing import Any, Generator, TypeVar, Union

from treq.response import _Response
from twisted.internet.defer import Deferred

A = TypeVar("A")

TreqResponse = _Response

# For use with Twisted's inlineCallbacks decorator; where mypy expects
# a Generator
TwistedDeferred = Generator[Deferred[Any], Any, A]

# mypy does not support recursive types so we can't say much about what's in
# the containers here.
JSON = Union[None, int, float, str, list, dict]
