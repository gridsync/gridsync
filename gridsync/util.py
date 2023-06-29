# -*- coding: utf-8 -*-
from __future__ import annotations

from binascii import hexlify, unhexlify
from datetime import datetime, timedelta
from html.parser import HTMLParser
from time import time
from traceback import format_exception
from typing import TYPE_CHECKING, Callable, Coroutine, Optional, TypeVar, Union

import attr
from twisted.internet.defer import Deferred, ensureDeferred, inlineCallbacks
from twisted.internet.interfaces import IReactorTime
from twisted.internet.task import deferLater
from twisted.python.failure import Failure

_T = TypeVar("_T")

B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


if TYPE_CHECKING:
    from gridsync.types_ import TwistedDeferred


def traceback(exc: Exception) -> str:
    return "".join(
        format_exception(type(exc), value=exc, tb=exc.__traceback__)
    )


def b58encode(b: bytes) -> str:  # Adapted from python-bitcoinlib
    n = int("0x0" + hexlify(b).decode("utf8"), 16)
    res = []
    while n:
        n, r = divmod(n, 58)
        res.append(B58_ALPHABET[r])
    rev = "".join(res[::-1])
    pad = 0
    for c in b:
        if c == 0:
            pad += 1
        else:
            break
    return B58_ALPHABET[0] * pad + rev


def b58decode(s: str) -> bytes:  # Adapted from python-bitcoinlib
    if not s:
        return b""
    n = 0
    for c in s:
        n *= 58
        if c not in B58_ALPHABET:
            raise ValueError(
                "Character '%r' is not a valid base58 character" % c
            )
        digit = B58_ALPHABET.index(c)
        n += digit
    h = "%x" % n
    if len(h) % 2:
        h = "0" + h
    res = unhexlify(h.encode("utf8"))
    pad = 0
    for c in s[:-1]:
        if c == B58_ALPHABET[0]:
            pad += 1
        else:
            break
    return b"\x00" * pad + res


def to_bool(s: str) -> bool:
    if s.lower() in ("false", "f", "no", "n", "off", "0", "none", ""):
        return False
    return True


def humanized_list(list_: list, kind: str = "files") -> Optional[str]:
    if not list_:
        return None
    if len(list_) == 1:
        return list_[0]
    if len(list_) == 2:
        return " and ".join(list_)
    if len(list_) == 3:
        return "{}, {}, and {}".format(*list_)
    return "{}, {}, and {} other {}".format(
        list_[0], list_[1], len(list_) - 2, kind
    )


def future_date(days_from_now: int) -> str:
    """
    Represent a future date as a short, human-friendlier string.

    Returns "Centuries" if the date is especially far into the future.
    """
    try:
        return datetime.strftime(
            datetime.strptime(
                datetime.isoformat(
                    datetime.now() + timedelta(days=days_from_now)
                ),
                "%Y-%m-%dT%H:%M:%S.%f",
            ),
            "%d %b %Y",
        )
    except OverflowError:  # Python int too large to convert to C int
        return "Centuries"


class _TagStripper(HTMLParser):  # pylint: disable=abstract-method
    def __init__(self) -> None:
        super().__init__()
        self.data: list = []

    def handle_data(self, data: str) -> None:
        self.data.append(data)

    def get_data(self) -> str:
        return "".join(self.data)


def strip_html_tags(s: str) -> str:
    ts = _TagStripper()
    ts.feed(s)
    return ts.get_data()


@inlineCallbacks
def until(
    predicate: Callable,
    result: bool = True,
    timeout: int = 10,
    period: float = 0.2,
    reactor: Optional[IReactorTime] = None,
) -> TwistedDeferred[object]:
    if reactor is None:
        from twisted.internet import reactor  # type: ignore
    limit = time() + timeout
    while time() < limit:
        if predicate() == result:
            return result
        yield deferLater(reactor, period, lambda: None)  # type: ignore
    raise TimeoutError(
        f'{predicate} did not return a value of "{result}" after waiting '
        f"{timeout} seconds"
    )


@attr.s
class Poller:
    """
    Poll some asynchronous function until it signals completion, then publish
    a notification to as many Deferreds as are waiting.

    :ivar clock: The reactor to use to schedule the polling.
    :ivar target: The asynchronous function to repeatedly call.
    :ivar interval: The minimum time, in seconds, between polling attempts.

    :ivar _idle: ``True`` if no code is waiting for completion notification,
        ``False`` if any code is.  This does not necessarily mean the
        asynchronous function is running at moment but it does mean this
        ``Poller`` will at least call it again soon.

    :ivar _waiting: The ``Deferred`` instances which will be fired to signal
        completion of the current polling attempt.
    """

    clock: IReactorTime = attr.ib()

    target: Callable[
        [],
        Union[
            Coroutine[Deferred[bool], _T, bool],
            Deferred[bool],
        ],
    ] = attr.ib()

    interval: float = attr.ib()
    _idle: bool = attr.ib(default=True)
    _waiting: list[Deferred[None]] = attr.ib(default=attr.Factory(list))

    def wait_for_completion(self) -> Deferred:
        """
        Wait for the target function to signal completion.  For a single
        ``Poller`` instance, any number of calls to this function will all
        share a single polling effort and the completion notification that
        results.

        :return: A ``Deferred`` on completion.
        """
        waiting: Deferred = Deferred()
        self._waiting.append(waiting)

        if self._idle:
            self._idle = False
            self._iterate_poll()

        return waiting

    @inlineCallbacks
    def _iterate_poll(self) -> TwistedDeferred[None]:
        """
        Poll the target function once.

        If it signals completion, deliver notifications.  If not, schedule
        another iteration.
        """
        try:
            ready = yield ensureDeferred(self.target())
            if ready:
                self._completed()
            else:
                self._schedule()
        except Exception:  # pylint: disable=broad-except
            self._deliver_result(Failure())

    def _completed(self) -> None:
        """
        Return to the idle state and deliver completion notification.
        """
        self._idle = True
        self._deliver_result(None)

    def _deliver_result(self, result: object) -> None:
        """
        Fire all waiting ``Deferred`` instances with the given result.
        """
        waiting = self._waiting
        self._waiting = []
        for w in waiting:
            w.callback(result)  # type: ignore

    def _schedule(self) -> None:
        """
        Schedule the next polling iteration.
        """
        deferLater(self.clock, self.interval, self._iterate_poll)
