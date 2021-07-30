# mypy: allow-any-explicit
from typing import Any, Generator, TypeVar

from treq.response import _Response
from twisted.internet.defer import Deferred

A = TypeVar("A")

TreqResponse = _Response

# For use with Twisted's inlineCallbacks decorator; where mypy expects
# a Generator
TwistedDeferred = Generator[Deferred[Any], Any, A]
