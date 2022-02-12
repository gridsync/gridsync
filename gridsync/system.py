from __future__ import annotations

import errno
import logging
import os
import shutil
import signal
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional, Tuple, Type, Union

from twisted.internet.defer import Deferred
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol

from gridsync import APP_NAME

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


def kill(pid: int = 0, pidfile: Optional[Union[Path, str]] = "") -> None:
    if pidfile:
        pidfile_path = Path(pidfile)
        try:
            pid = int(pidfile_path.read_text(encoding="utf-8"))
        except (EnvironmentError, ValueError) as err:
            logging.error("Error loading pid from %s: %s", pidfile, str(err))
            return
    logging.debug("Trying to kill PID %i...", pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as err:
        if err.errno not in (errno.ESRCH, errno.EINVAL):
            logging.error("Error killing PID %i: %s", pid, str(err))
            raise
        logging.warning("Could not kill PID %i: %s", pid, str(err))
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
    def __init__(
        self,
        callback_triggers: Optional[List[str]] = None,
        errback_triggers: Optional[List[Tuple[str, Type[Exception]]]] = None,
        stdout_line_collector: Optional[Callable] = None,
        stderr_line_collector: Optional[Callable] = None,
    ) -> None:
        self.callback_triggers = callback_triggers
        self.errback_triggers = errback_triggers
        self.stdout_line_collector = stdout_line_collector
        self.stderr_line_collector = stderr_line_collector
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
        if self.done.called:
            return
        if isinstance(reason.value, ProcessDone):
            self.done.callback(self._output.getvalue().decode("utf-8").strip())
        else:
            self.done.errback(reason)
