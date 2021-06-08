from __future__ import annotations

import errno
import json
import logging
import os
import shutil
import signal
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import treq
from autobahn.twisted.websocket import (
    WebSocketClientFactory, WebSocketClientProtocol
)
from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.endpoints import TCP4ClientEndpoint
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


class MagicFolderWebError(MagicFolderError):
    pass


class MagicFolderWebSocketClientProtocol(WebSocketClientProtocol):
    def onOpen(self):
        logging.debug("WebSocket connection opened.")

    def onMessage(self, payload, isBinary):
        if not isBinary:
            logging.debug(payload.decode("utf8"))


class MagicFolderProcessProtocol(ProcessProtocol):
    def __init__(self, callback_trigger: str = "") -> None:
        self.trigger = callback_trigger
        self.done = Deferred()
        self.output = BytesIO()
        self.port: int = 0

    def outReceived(self, data: bytes) -> None:
        self.output.write(data)
        decoded = data.decode()
        for line in decoded.strip().split("\n"):
            if "Site starting on " in line and not self.port:  # XXX
                try:
                    self.port = int(line.split(" ")[-1])
                except ValueError:
                    pass
            if not self.done.called and self.trigger and self.trigger in line:
                self.done.callback((self.transport.pid, self.port))  # type: ignore

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


class MagicFolderStatusMonitor(MultiService):
    def __init__(self, magic_folder: MagicFolder) -> None:
        super().__init__()
        self.magic_folder = magic_folder

        self._client_service = None

    def _create_client_service(self):
        endpoint = TCP4ClientEndpoint(
            reactor, "127.0.0.1", self.magic_folder.port
        )
        factory = WebSocketClientFactory(
            f"ws://127.0.0.1:{self.magic_folder.port}/v1/status",
            headers={"Authorization": f"Bearer {self.magic_folder.api_token}"},
        )
        factory.protocol = MagicFolderWebSocketClientProtocol
        client_service = ClientService(endpoint, factory, clock=reactor)
        return client_service

    def stop(self):
        if self.running:
            self._client_service.disownServiceParent()
            self._client_service = None
            return super().stopService()
        return None

    def start(self):
        if not self.running:
            self._client_service = self._create_client_service()
            self._client_service.setServiceParent(self)
            return super().startService()
        return None


class MagicFolder:
    def __init__(self, gateway: Tahoe, executable: Optional[str] = "") -> None:
        self.gateway = gateway
        self.executable = executable

        self.configdir = Path(gateway.nodedir, "private", "magic-folder")
        self.pid: int = 0
        self.port: int = 0
        self.config: dict = {}
        self.api_token: str = ""
        self.monitor = MagicFolderStatusMonitor(self)

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
    def _request(self, method: str, path: str) -> TwistedDeferred[dict]:
        if not self.api_token:
            raise MagicFolderWebError("API token not found")
        if not self.port:
            raise MagicFolderWebError("API port not found")
        resp = yield treq.request(
            method,
            f"http://127.0.0.1:{self.port}/v1{path}",
            headers={"Authorization": f"Bearer {self.api_token}"},
        )
        content = yield treq.content(resp)
        if resp.code == 200:
            return json.loads(content)
        else:
            raise MagicFolderWebError(
                f"Error {resp.code} requesting {method} {path}: {content}"
            )

    @inlineCallbacks
    def get_folders(self) -> TwistedDeferred[Dict[str, dict]]:
        folders = yield self._request(
            "GET", "/magic-folder?include_secret_information=1"
        )
        return folders

    @inlineCallbacks
    def _load_config(self) -> TwistedDeferred[None]:
        config_output = yield self.command(["show-config"])
        self.config = json.loads(config_output)
        self.api_token = self.config.get("api_token", "")
        if not self.api_token:
            raise MagicFolderError("Could not load magic-folder API token")

    def stop(self) -> None:
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
                ["init", "-l", "tcp:0", "-n", self.gateway.nodedir]
            )
        result = yield self.command(
            ["run"], "Completed initial Magic Folder setup"
        )
        pid, self.port = result
        with open(pidfile, "w") as f:
            f.write(str(pid))
        yield self._load_config()
        self.monitor.start()
