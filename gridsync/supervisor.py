import logging
import os
from pathlib import Path
from typing import Callable, List, Optional

from atomicwrites import atomic_write
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync.system import SubprocessProtocol, terminate
from gridsync.types import TwistedDeferred


class Supervisor:
    def __init__(
        self,
        pidfile: Optional[Path] = None,
        restart_delay: int = 1,
    ) -> None:
        self.pidfile = pidfile
        self.restart_delay: int = restart_delay
        self.pid: Optional[int] = None
        self._keep_alive: bool = True
        self._args: List[str] = []
        self._started_trigger = ""
        self._stdout_line_collector: Optional[Callable] = None
        self._stderr_line_collector: Optional[Callable] = None
        self._process_started_callback: Optional[Callable] = None
        self._on_process_ended: Optional[Callable] = None

    @inlineCallbacks
    def stop(self) -> TwistedDeferred[None]:
        self._keep_alive = False
        if not self.pid and self.pidfile and self.pidfile.exists():
            self.pid = int(self.pidfile.read_text(encoding="utf-8"))
        if not self.pid:
            logging.warning(
                "Tried to stop a supervised process that wasn't running"
            )
            return
        logging.debug("Stopping supervised process: %s", " ".join(self._args))
        yield terminate(self.pid, kill_after=5)
        if self.pidfile and self.pidfile.exists():
            self.pidfile.unlink()
        logging.debug("Supervised process stopped: %s", " ".join(self._args))
        self.pid = None

    @inlineCallbacks
    def _start_process(self) -> TwistedDeferred[int]:
        self._keep_alive = True
        protocol = SubprocessProtocol(
            callback_triggers=[self._started_trigger],
            stdout_line_collector=self._stdout_line_collector,
            stderr_line_collector=self._stderr_line_collector,
            on_process_ended=self._schedule_restart,
        )
        transport = yield reactor.spawnProcess(  # type: ignore
            protocol, self._args[0], args=self._args, env=os.environ
        )
        if self._started_trigger:
            yield protocol.done
        else:
            # To prevent unhandled ProcessTerminated errors
            protocol.done.callback(None)
        pid = transport.pid
        if self.pidfile:
            with atomic_write(self.pidfile, mode="w", overwrite=True) as f:
                f.write(str(pid))
        logging.debug(
            "Supervised process (re)started: %s (PID %i)",
            "".join(self._args),
            pid,
        )
        self.pid = pid
        if self._process_started_callback:
            self._process_started_callback()
        return pid

    def _schedule_restart(self, _) -> None:  # type: ignore
        if self._keep_alive:
            logging.debug(
                "Restarting supervised process: %s", "".join(self._args)
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
        process_started_callback: Optional[Callable] = None,
    ) -> TwistedDeferred[int]:

        self._args = args
        self._started_trigger = started_trigger
        self._stdout_line_collector = stdout_line_collector
        self._stderr_line_collector = stderr_line_collector
        self._process_started_callback = process_started_callback

        if self.pidfile and self.pidfile.exists():
            yield self.stop()
        logging.debug("Starting supervised process: %s", "".join(self._args))
        pid = yield self._start_process()
        return pid

    def restart(self) -> None:
        pass
