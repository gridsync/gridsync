from __future__ import annotations

import errno
import logging
import os
import signal
from io import BytesIO
from pathlib import Path
from subprocess import SubprocessError
from typing import TYPE_CHECKING, Callable, Dict, Optional, Type, Union

from twisted.internet.defer import Deferred
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol

if TYPE_CHECKING:
    from twisted.python.failure import Failure


def kill(pid: int = 0, pidfile: Optional[Union[Path, str]] = "") -> None:
    if pidfile:
        pidfile_path = Path(pidfile)
        try:
            pid = int(pidfile_path.read_text())
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
        callback_trigger: str = "",
        errback_trigger: str = "",
        errback_exception: Type[Exception] = SubprocessError,
        collector: Optional[Callable] = None,
        collectors: Optional[Dict[int, Callable]] = None,
        line_collectors: Optional[Dict[int, Callable]] = None,
    ) -> None:
        self.callback_trigger = callback_trigger
        self.errback_trigger = errback_trigger
        self.errback_exception = errback_exception
        self.collector = collector
        self.collectors = collectors
        self.line_collectors = line_collectors
        self.output = BytesIO()
        self.done = Deferred()

    def callback(self) -> None:
        self.done.callback(self.output.getvalue().decode("utf-8").strip())

    def errback(self) -> None:
        self.done.errback(
            self.errback_exception(
                self.output.getvalue().decode("utf-8").strip()
            )
        )

    def childDataReceived(self, childFD: int, data: bytes) -> None:
        if not self.done.called:
            self.output.write(data)
        for line in data.decode("utf-8").strip().split("\n"):
            if not line:
                continue
            if self.collector:
                self.collector(line)
            if self.line_collectors and childFD in self.line_collectors:
                line_collector = self.line_collectors.get(childFD)
                if line_collector:
                    line_collector(line)
            if self.done.called:
                continue
            if self.callback_trigger and self.callback_trigger in line:
                self.callback()
            elif self.errback_trigger and self.errback_trigger in line:
                self.errback()
        if self.collectors and childFD in self.collectors:
            collector = self.collectors.get(childFD)
            if collector:
                collector(data)

    def processEnded(self, reason: Failure) -> None:
        if self.done.called:
            return
        if isinstance(reason.value, ProcessDone):
            self.callback()
        else:
            self.errback()

    def processExited(self, reason: Failure) -> None:
        self.processEnded(reason)
