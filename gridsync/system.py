from __future__ import annotations

import logging
import shutil
import time
from io import BytesIO
from typing import TYPE_CHECKING, Callable, Optional, Union

from psutil import NoSuchProcess, Process, TimeoutExpired
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList, inlineCallbacks
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater

from gridsync import APP_NAME
from gridsync.types_ import TwistedDeferred

if TYPE_CHECKING:
    from twisted.python.failure import Failure


def which(cmd: str) -> str:
    """
    Return the path to an executable which would be run if the given
    cmd was called. If a version of the executable exists whose name is
    prefixed with the name of this application (e.g., "Gridsync-tahoe"),
    prefer and return that path instead. If no such paths can be found,
    raise an EnvironmentError.

    :param str cmd: The command
    :return str: The path to the executable
    """
    path = shutil.which(f"{APP_NAME}-{cmd}") or shutil.which(cmd)
    if not path:
        raise EnvironmentError(
            f'Could not find a "{cmd}" (or "{APP_NAME}-{cmd}") executable. '
            "Please ensure that it exists on your PATH."
        )
    return path


@inlineCallbacks
def terminate_if_matching(  # noqa: max-complexity
    pid: int,
    create_time: float,
    kill_after: Optional[Union[int, float]] = None,
) -> TwistedDeferred[bool]:
    """
    Terminate the process at `pid` only if `create_time` matches its
    creation time.

    :returns: Deferred that fires when the process has exited or been
        killed. If it was killed, True is returned; otherwise, False.
    """
    try:
        proc = Process(pid)
        if proc.create_time() != create_time:
            return False
        proc.terminate()
    except NoSuchProcess:
        return False

    limit = time.time() + kill_after if kill_after else 0
    while proc.is_running():
        try:
            if proc.wait(timeout=0) in (None, 0):
                return False
            return True
        except NoSuchProcess:
            break
        except TimeoutExpired:
            pass
        if limit and time.time() >= limit:
            try:
                proc.kill()
            except NoSuchProcess:
                return False
        yield deferLater(reactor, 0.1, lambda: None)  # type: ignore
    return False  # appease mypy; we shouldn't get here


@inlineCallbacks
def terminate(
    proc: SubprocessProtocol, kill_after: Optional[Union[int, float]] = None
) -> TwistedDeferred[None]:
    """
    Terminate the running process given by its protocol.

    :returns: a Deferred that fires when the process has terminated or been killed.
    """
    # mypy is very confused by zope.interface
    proc.transport.signalProcess("TERM")  # type:ignore

    waiting = [proc.when_exited()]
    if kill_after:
        waiting.append(deferLater(reactor, kill_after, lambda: None))  # type: ignore
    _, idx = yield DeferredList(
        waiting, fireOnOneCallback=True, fireOnOneErrback=True
    )
    if idx > 0:
        # the timeout fired (not when_exited())
        logging.debug(
            "Failed to terminate, sending KILL to %i",
            proc.transport.pid,  # type:ignore
        )
        proc.transport.signalProcess("KILL")  # type:ignore
        try:
            yield proc.when_exited()
        except Exception:  # pylint: disable=broad-except
            pass


class SubprocessError(Exception):
    pass


class SubprocessProtocol(ProcessProtocol):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        callback_triggers: Optional[list[str]] = None,
        errback_triggers: Optional[list[tuple[str, type[Exception]]]] = None,
        stdout_line_collector: Optional[Callable] = None,
        stderr_line_collector: Optional[Callable] = None,
        on_process_ended: Optional[Callable] = None,
    ) -> None:
        self.callback_triggers = callback_triggers
        self.errback_triggers = errback_triggers
        self.stdout_line_collector = stdout_line_collector
        self.stderr_line_collector = stderr_line_collector
        self._on_process_ended = on_process_ended
        self._output = BytesIO()
        self.done: Deferred = Deferred()
        # becomes None once we've exited
        self._awaiting_ended: Optional[list[Deferred]] = []

    def _check_triggers(self, line: str) -> None:
        if self.callback_triggers:
            for text in self.callback_triggers:
                if text and text in line:
                    self.done.callback(
                        self._output.getvalue().decode("utf-8").strip()
                    )
        if self.errback_triggers:
            for pair in self.errback_triggers:
                if not pair:
                    continue
                text, exception = pair
                if text and exception and text in line:
                    self.done.errback(
                        exception(
                            self._output.getvalue().decode("utf-8").strip()
                        )
                    )

    def childDataReceived(self, childFD: int, data: bytes) -> None:
        if not self.done.called:
            self._output.write(data)
        for line in data.decode("utf-8").strip().split("\n"):
            if self.stdout_line_collector and childFD == 1:
                self.stdout_line_collector(line)
            elif self.stderr_line_collector and childFD == 2:
                self.stderr_line_collector(line)
            if not self.done.called:
                self._check_triggers(line)

    def when_exited(self) -> Deferred[None]:
        """
        :returns: a Deferred that fires when this process has exited
        """
        d: Deferred[None] = Deferred()
        if self._awaiting_ended is None:
            # already exited
            d.callback(None)
        else:
            self._awaiting_ended.append(d)
        return d

    def processEnded(self, reason: Failure) -> None:
        if not self.done.called:
            output = self._output.getvalue().decode("utf-8").strip()
            if isinstance(reason.value, ProcessDone):
                self.done.callback(output)
            else:
                self.done.errback(SubprocessError(output))
        if self._on_process_ended:
            self._on_process_ended(reason)
        if self._awaiting_ended:
            notify = self._awaiting_ended
            self._awaiting_ended = None
            for d in notify:
                d.callback(None)
