from __future__ import annotations

import errno
import json
import signal
import logging
import os
import shutil
import socket
from io import BytesIO
from pathlib import Path
from random import randint
from typing import TYPE_CHECKING, List, Optional

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol

if TYPE_CHECKING:
    from twisted.python.failure import Failure

    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred


def randport(
    port: int = 0, range_min: int = 49152, range_max: int = 65535
) -> int:
    if not port:
        port = randint(range_min, range_max)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                logging.debug("Trying to bind to port: %i", port)
                s.bind(("127.0.0.1", port))
            except socket.error as err:
                logging.debug("Couldn't bind to port %i: %s", port, err)
                if err.errno == errno.EADDRINUSE:
                    port = randint(range_min, range_max)
                    continue
                raise
            logging.debug("Port %s is free", port)
            return port


class MagicFolderError(Exception):
    pass


class MagicFolderProcessError(MagicFolderError):
    pass


class MagicFolderProcessProtocol(ProcessProtocol):
    def __init__(self, callback_trigger: str = "") -> None:
        self.trigger = callback_trigger
        self.done = Deferred()
        self.output = BytesIO()

    def outReceived(self, data: bytes) -> None:
        self.output.write(data)
        decoded = data.decode()
        for line in decoded.strip().split("\n"):
            print("#############", line)
            if not self.done.called and self.trigger and self.trigger in line:
                self.done.callback(self.transport.pid)  # type: ignore

    def errReceived(self, data: bytes) -> None:
        self.outReceived(data)

    def processEnded(self, reason: Failure) -> None:
        if not self.done.called:
            self.done.callback(self.output.getvalue().decode().strip())

    def processExited(self, reason: Failure) -> None:
        if not self.done.called and not isinstance(reason.value, ProcessDone):
            self.done.errback(
                MagicFolderProcessError(
                    self.output.getvalue().decode().strip()
                )
            )


class MagicFolder:
    def __init__(self, gateway: Tahoe, executable: Optional[str] = "") -> None:
        self.gateway = gateway
        self.executable = executable

        self.configdir = Path(gateway.nodedir, "private", "magic-folder")
        self.pid: int = 0
        self.port: int = 0
        self.api_token: str = ""

    @inlineCallbacks
    def command(
        self, args: List[str], callback_trigger: str = ""
    ) -> TwistedDeferred[str]:
        if not self.executable:
            self.executable = shutil.which("magic-folder")
        if not self.executable:
            raise EnvironmentError(
                'Could not find "magic-folder" executable on PATH.'
            )
        args = [self.executable, f"--config={self.configdir}"] + args
        env = os.environ
        env["PYTHONUNBUFFERED"] = "1"
        logging.debug("Executing %s...", " ".join(args))
        protocol = MagicFolderProcessProtocol(callback_trigger)
        reactor.spawnProcess(  # type: ignore
            protocol, self.executable, args=args, env=env
        )
        output = yield protocol.done  # type: ignore
        return output

    @inlineCallbacks
    def version(self) -> TwistedDeferred[str]:
        output = yield self.command(["--version"])
        return output

    @inlineCallbacks
    def _load_config(self) -> TwistedDeferred[None]:
        config_output = yield self.command(["show-config"])
        config = json.loads(config_output)
        self.api_token = config.get("api_token", "")
        if not self.api_token:
            raise MagicFolderError("Could not load magic-folder API token")
        api_endpoint = config.get("api_endpoint", "")
        if not api_endpoint:
            raise MagicFolderError("Could not load magic-folder API endpoint")
        try:
            self.api_port = int(api_endpoint.split(":")[-1])
        except ValueError:
            raise MagicFolderError(
                "Could not parse port from magic-folder API endpoint"
            )

    def stop(self):
        pidfile = Path(self.configdir, "magic-folder.pid")
        try:
            with open(pidfile, "r") as f:
                pid = int(f.read())
        except (EnvironmentError, ValueError) as err:
            logging.warning("Error loading magic-folder.pid: %s", str(err))
            return
        logging.debug("Trying to kill PID %d...", pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as err:
            if err.errno not in (errno.ESRCH, errno.EINVAL):
                logging.error(err)
        try:
            pidfile.unlink()
        except OSError as err:
            logging.warning("Error removing magic-folder.pid: %s", err)

    @inlineCallbacks
    def start(self) -> TwistedDeferred[None]:
        logging.debug("Starting magic-folder...")
        pidfile = Path(self.configdir, "magic-folder.pid")
        if pidfile.exists():
            self.stop()
        if not self.configdir.exists():
            yield self.command(
                ["init", "-l", f"tcp:{randport()}", "-n", self.gateway.nodedir]
            )
        self.pid = yield self.command(
            ["run"], "Completed initial Magic Folder setup"
        )
        with open(pidfile, "w") as f:
            f.write(str(self.pid))
        yield self._load_config()
