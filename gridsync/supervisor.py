import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional

from psutil import Process
from atomicwrites import atomic_write
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync.system import (
    SubprocessProtocol,
    terminate,
    terminate_if_matching,
)
from gridsync.types import TwistedDeferred


class Supervisor:
    def __init__(
        self,
        pidfile: Optional[Path] = None,
        restart_delay: int = 1,
    ) -> None:
        self.pidfile = pidfile
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

    @property
    def process(self) -> Optional[Process]:
        if self._process is None:
            if self._protocol is not None:
                self._process = Process(self._protocol.transport.pid)
        return self._process

    @property
    def name(self):
        if self._protocol is None:
            return ""
        return self.process.name

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        self._keep_alive = False
        if self._protocol is None:
            # nothing is currently running, but perhaps the PID-file
            # thinks something is running.
            if self.pidfile and self.pidfile.exists():
                contents = self.pidfile.read_text(encoding="utf-8")
                words = contents.split()
                pid = int(words[0])
                pid_create_time = float(words[1])
                terminate_if_matching(pid, pid_create_time, kill_after=5)

        if self._protocol is None:
            logging.warning(
                "Tried to stop a supervised process that wasn't running"
            )
            return

        logging.debug("Stopping supervised process: %s", " ".join(self._args))
        yield terminate(self._protocol, kill_after=5)

        if self.pidfile and self.pidfile.exists():
            logging.debug("Removing pidfile: %s", str(self.pidfile))
            self.pidfile.unlink()
            logging.debug("Pidfile removed: %s", str(self.pidfile))
        logging.debug("Supervised process stopped: %s", " ".join(self._args))
        self._protocol = None
        self._process = None

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
        transport = yield reactor.spawnProcess(  # type: ignore
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
        if self.pidfile:
            with atomic_write(self.pidfile, mode="w", overwrite=True) as f:
                f.write(f"{self.process.pid} {self.process.create_time()}\n")
            logging.debug(
                'Wrote "%s %s" to pidfile: %s',
                self.process.pid,
                self.process.create_time(),
                str(self.pidfile),
            )
        logging.debug(
            "Supervised process (re)started: %s (PID %i)",
            " ".join(self._args),
            self.process.pid,
        )
        if self._call_after_start:
            self._call_after_start()
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

        if self.pidfile and self.pidfile.exists():
            yield self.stop()
        logging.debug("Starting supervised process: %s", " ".join(self._args))
        result = yield self._start_process()
        pid, name = result
        return (pid, name)
