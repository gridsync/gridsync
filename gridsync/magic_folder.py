from __future__ import annotations

import errno
import json
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
    def start(self) -> TwistedDeferred[None]:
        logging.debug("Starting magic-folder...")
        if not self.configdir.exists():
            yield self.command(
                ["init", "-l", f"tcp:{randport()}", "-n", self.gateway.nodedir]
            )
        self.pid = yield self.command(
            ["run"], "Completed initial Magic Folder setup"
        )
        with open(Path(self.configdir, "magic-folder.pid"), "w") as f:
            f.write(str(self.pid))
