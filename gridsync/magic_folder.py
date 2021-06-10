from __future__ import annotations

import json
import logging
import os
import shutil
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import treq
from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
)
from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol

from gridsync.system import kill

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


class MagicFolderWebSocketClientProtocol(
    WebSocketClientProtocol
):  # pylint: disable=too-many-ancestors
    def onOpen(self) -> None:
        logging.debug("WebSocket connection opened.")

    def onMessage(self, payload: bytes, isBinary: bool) -> None:
        if isBinary:
            logging.warning(
                "Received a binary-mode WebSocket message from magic-folder "
                "status API; dropping."
            )
            return
        msg = payload.decode("utf-8")
        logging.debug("WebSocket message received: %s", msg)
        self.factory.magic_folder.on_message_received(msg)

    def onClose(self, wasClean: bool, code: int, reason: str) -> None:
        logging.debug(
            "WebSocket connection closed: %s (code %s)", reason, code
        )


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
            logging.debug("[magic-folder] %s", line)  # XXX
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

        self._client_service: Optional[ClientService] = None

    def _create_client_service(self) -> ClientService:
        endpoint = TCP4ClientEndpoint(
            reactor, "127.0.0.1", self.magic_folder.port
        )
        factory = WebSocketClientFactory(
            f"ws://127.0.0.1:{self.magic_folder.port}/v1/status",
            headers={"Authorization": f"Bearer {self.magic_folder.api_token}"},
        )
        factory.protocol = MagicFolderWebSocketClientProtocol
        factory.magic_folder = self.magic_folder
        client_service = ClientService(endpoint, factory, clock=reactor)
        return client_service

    def stop(self) -> None:
        if self.running and self._client_service:
            self._client_service.disownServiceParent()
            self._client_service = None
            return super().stopService()
        return None

    def start(self) -> None:
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
        self.pidfile = Path(self.configdir, "magic-folder.pid")
        self.pid: int = 0
        self.port: int = 0
        self.config: dict = {}
        self.api_token: str = ""
        self.monitor = MagicFolderStatusMonitor(self)

    @staticmethod
    def on_message_received(msg: str) -> None:
        print("###########", msg)

    @inlineCallbacks
    def _command(
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
        output = yield self._command(["--version"])
        return output

    @inlineCallbacks
    def add_folder(
        self,
        path: str,
        author: str,
        name: Optional[str] = "",
        poll_interval: int = 60,
    ) -> TwistedDeferred[None]:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if not name:
            name = p.name
        yield self._command(
            [
                "add",
                f"--author={author}",
                f"--name={name}",
                f"--poll-interval={poll_interval}",
                str(p.resolve()),
            ]
        )

    @inlineCallbacks
    def _request(
        self, method: str, path: str, body: bytes = b""
    ) -> TwistedDeferred[dict]:
        if not self.api_token:
            raise MagicFolderWebError("API token not found")
        if not self.port:
            raise MagicFolderWebError("API port not found")
        resp = yield treq.request(
            method,
            f"http://127.0.0.1:{self.port}/v1{path}",
            headers={"Authorization": f"Bearer {self.api_token}"},
            data=body,
        )
        content = yield treq.content(resp)
        if resp.code == 200:
            return json.loads(content)
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
    def get_snapshots(self) -> TwistedDeferred[Dict[str, dict]]:
        snapshots = yield self._request("GET", "/snapshot")
        return snapshots

    @inlineCallbacks
    def get_participants(
        self, folder_name: str
    ) -> TwistedDeferred[Dict[str, dict]]:
        participants = yield self._request(
            "GET", f"/magic-folder/{folder_name}/participants"
        )
        return participants

    @inlineCallbacks
    def add_participant(
        self, folder_name: str, author_name: str, personal_dmd: str
    ) -> TwistedDeferred[None]:
        data = {"author": {"name": author_name}, "personal_dmd": personal_dmd}
        yield self._request(
            "POST",
            f"/magic-folder/{folder_name}/participants",
            body=json.dumps(data).encode("utf-8"),
        )

    @inlineCallbacks
    def _load_config(self) -> TwistedDeferred[None]:
        config_output = yield self._command(["show-config"])
        self.config = json.loads(config_output)
        self.api_token = self.config.get("api_token", "")
        if not self.api_token:
            raise MagicFolderError("Could not load magic-folder API token")

    def stop(self) -> None:
        kill(pidfile=self.pidfile)

    @inlineCallbacks
    def start(self) -> TwistedDeferred[None]:
        logging.debug("Starting magic-folder...")
        if self.pidfile.exists():
            self.stop()
        if not self.configdir.exists():
            yield self._command(
                [
                    "init",
                    "-l",
                    "tcp:0:interface=127.0.0.1",
                    "-n",
                    self.gateway.nodedir,
                ]
            )
        result = yield self._command(
            ["run"], "Completed initial Magic Folder setup"
        )
        pid, self.port = result
        with open(self.pidfile, "w") as f:
            f.write(str(pid))
        yield self._load_config()
        self.monitor.start()
