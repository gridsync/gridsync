from __future__ import annotations

import errno
import logging
import shutil
import time
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Type, Union

from psutil import NoSuchProcess, Process, TimeoutExpired
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater

from gridsync import APP_NAME
from gridsync.types import TwistedDeferred

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
def terminate(
    pid: int, kill_after: Optional[Union[int, float]] = None
) -> TwistedDeferred[None]:
    try:
        proc = Process(pid)
    except NoSuchProcess:
        return
    if kill_after:
        limit = time.time() + kill_after
    else:
        limit = 0
    try:
        proc.terminate()
    except NoSuchProcess:
        return
    time_started = time.time()
    while proc.is_running():
        try:
            return proc.wait(timeout=0)
        except NoSuchProcess:
            return
        except TimeoutExpired:
            pass
        if limit and time.time() >= limit:
            try:
                proc.kill()
            except NoSuchProcess:
                return
        yield deferLater(reactor, 0.1, lambda: None)  # type: ignore


def kill(pid: int = 0, pidfile: Optional[Union[Path, str]] = "") -> None:
    if pidfile:
        pidfile_path = Path(pidfile)
        try:
            pid = int(pidfile_path.read_text(encoding="utf-8"))
        except (EnvironmentError, ValueError) as err:
            logging.error("Error loading pid from %s: %s", pidfile, str(err))
            return
    logging.debug("Trying to kill PID %i...", pid)
    proc = Process(pid)
    try:
        proc.terminate()
    except OSError as err:
        if err.errno not in (errno.ESRCH, errno.EINVAL):
            logging.error("Error killing PID %i: %s", pid, str(err))
            raise
        logging.warning("Could not kill PID %i: %s", pid, str(err))
    proc.wait(timeout=3)
    try:
        proc.kill()
    except NoSuchProcess:
        pass
    if pidfile:
        logging.debug("Removing pidfile: %s", str(pidfile))
        try:
            pidfile_path.unlink()
        except OSError as err:
            logging.warning(
                "Error removing pidfile %s: %s", str(pidfile), str(err)
            )
            return
        logging.debug("Successfully removed pidfile: %s", str(pidfile))


class SubprocessProtocol(ProcessProtocol):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        callback_triggers: Optional[List[str]] = None,
        errback_triggers: Optional[List[Tuple[str, Type[Exception]]]] = None,
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

    def processEnded(self, reason: Failure) -> None:
        if not self.done.called:
            if isinstance(reason.value, ProcessDone):
                self.done.callback(
                    self._output.getvalue().decode("utf-8").strip()
                )
            else:
                self.done.errback(reason)
        if self._on_process_ended:
            self._on_process_ended(reason)
