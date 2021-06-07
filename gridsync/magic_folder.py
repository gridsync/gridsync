from __future__ import annotations

import logging
import os
import shutil
from io import BytesIO
from typing import TYPE_CHECKING, List, Optional

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol

if TYPE_CHECKING:
    from twisted.python.failure import Failure

    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred


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
        args = [self.executable] + args
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
        version = yield self.version()
        logging.debug("!!!!!!!!!!!!!!!!!!!!!!!!!! Found: %s", version)  # XXX
