import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional

from filelock import FileLock
from psutil import Process
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync.system import (
    SubprocessProtocol,
    terminate,
    terminate_if_matching,
)
from gridsync.types_ import TwistedDeferred


def parse_pidfile(pidfile: Path) -> tuple[int, float]:
    """
    :param Path pidfile:
    :returns tuple: 2-tuple of pid, creation-time as int, float
    :raises ValueError: on error
    """
    with pidfile.open("r") as f:
        content = f.read().strip()
    try:
        pid_str, starttime_str = content.split()
        pid = int(pid_str)
        starttime = float(starttime_str)
    except ValueError as e:
        raise ValueError("found invalid PID file in {}".format(pidfile)) from e
    return pid, starttime


class Supervisor:
    def __init__(
        self,
        pidfile: Path,
        restart_delay: int = 1,
    ) -> None:
        self.pidfile: Path = pidfile
        self.restart_delay: int = restart_delay
        self.time_started: Optional[float] = None
        # _protocol is non-None only when we have a running subprocess
        self._protocol: Optional[SubprocessProtocol] = None
        # _process lazily created to match _protocol.pid
        self._process: Optional[Process] = None
        self._keep_alive: bool = True
        self._args: list[str] = []
        self._started_trigger = ""
        self._stdout_line_collector: Optional[Callable] = None
        self._stderr_line_collector: Optional[Callable] = None
        self._call_before_start: Optional[Callable] = None
        self._call_after_start: Optional[Callable] = None
        self._on_process_ended: Optional[Callable] = None

    def is_running(self) -> bool:
        return self.process.is_running() if self.process else False

    @property
    def process(self) -> Optional[Process]:
        if self._process is None:
            if self._protocol is not None:
                self._process = Process(self._protocol.transport.pid)  # type: ignore
        return self._process

    @property
    def name(self) -> str:
        if self.process is None:
            return ""
        return self.process.name

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        self._keep_alive = False
        if self._protocol is None:
            logging.warning(
                "Tried to stop a supervised process that wasn't running"
            )
            return
        logging.debug("Stopping supervised process: %s", " ".join(self._args))
        yield terminate(self._protocol, kill_after=5)
        self._protocol = None
        self._process = None
        logging.debug("Supervised process stopped: %s", " ".join(self._args))

    @inlineCallbacks
    def _start_process(self) -> TwistedDeferred[tuple[int, str]]:
        self._keep_alive = True
        protocol = SubprocessProtocol(
            callback_triggers=[self._started_trigger],
            stdout_line_collector=self._stdout_line_collector,
            stderr_line_collector=self._stderr_line_collector,
            on_process_ended=self._schedule_restart,
        )
        if self._call_before_start:
            self._call_before_start()
        yield reactor.spawnProcess(  # type: ignore
            protocol, self._args[0], args=self._args, env=os.environ
        )
        self._protocol = protocol
        self._process = None  # lazily re-created
        # note: we need to set self._protocol _before_ anything else
        # async so that stop() can work properly
        self.time_started = time.time()

        if self._started_trigger:
            yield protocol.done
        else:
            # To prevent unhandled ProcessTerminated errors
            protocol.done.callback(None)
        logging.debug(
            "Supervised process (re)started: %s (PID %i)",
            " ".join(self._args),
            self.process.pid,  # type: ignore
        )
        if self._call_after_start:
            self._call_after_start()
        assert self.process is not None
        return (self.process.pid, self.name)

    def _schedule_restart(self, _) -> None:  # type: ignore
        if self._keep_alive:
            logging.debug(
                "Restarting supervised process: %s", " ".join(self._args)
            )
            reactor.callLater(  # type: ignore
                self.restart_delay, self._start_process
            )

    @inlineCallbacks
    def start(  # pylint: disable=too-many-arguments
        self,
        args: list[str],
        started_trigger: str = "",
        stdout_line_collector: Optional[Callable] = None,
        stderr_line_collector: Optional[Callable] = None,
        call_before_start: Optional[Callable] = None,
        call_after_start: Optional[Callable] = None,
    ) -> TwistedDeferred[tuple[int, str]]:
        self._args = args
        self._started_trigger = started_trigger
        self._stdout_line_collector = stdout_line_collector
        self._stderr_line_collector = stderr_line_collector
        self._call_before_start = call_before_start
        self._call_after_start = call_after_start

        # examine our process' corresponding pidfile, which means one
        # of these is true:
        #  1. there is no pidfile
        #  2. the pid doesn't exist as a process
        #  3. the pid is a tahoe (or magic-folder etc) process
        #  4. the pid is some other process

        lockfile = self.pidfile.with_name(self.pidfile.name + ".lock")
        with FileLock(lockfile, timeout=2):
            try:
                pid, create = parse_pidfile(self.pidfile)
            except ValueError:
                logging.warning(
                    "Removing invalid pidfile: %s",
                    self.pidfile,
                )
                self.pidfile.unlink()
            except OSError:
                # 1. no pidfile
                pass
            else:
                # the pidfile exists: if it's a leftover one, kill it
                # (which is case 3)
                yield terminate_if_matching(pid, create, kill_after=5)
                # we're either case 3 or 4 here, and either way want
                # to remove the file so our subprocess can start
                self.pidfile.unlink()

        logging.debug("Starting supervised process: %s", " ".join(self._args))
        result = yield self._start_process()
        pid, name = result
        return (pid, name)
