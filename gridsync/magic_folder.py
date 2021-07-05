from __future__ import annotations

import json
import logging
import os
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    DefaultDict,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import treq
from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
)
from PyQt5.QtCore import QObject, pyqtSignal
from twisted.application.internet import ClientService
from twisted.application.service import MultiService
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.task import deferLater

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred

from gridsync.crypto import randstr
from gridsync.system import SubprocessProtocol, kill


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
        self.factory.magic_folder.monitor.on_status_message_received(msg)

    def onClose(self, wasClean: bool, code: int, reason: str) -> None:
        logging.debug(
            "WebSocket connection closed: %s (code %s)", reason, code
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


class MagicFolderMonitor(QObject):

    synchronizing_state_changed = pyqtSignal(bool)
    sync_started = pyqtSignal()
    sync_stopped = pyqtSignal()

    folder_added = pyqtSignal(str)  # folder
    folder_removed = pyqtSignal(str)  # folder

    def __init__(self, magic_folder: MagicFolder) -> None:
        super().__init__()
        self.magic_folder = magic_folder
        self.status_monitor = MagicFolderStatusMonitor(magic_folder)
        self.folders: Dict[str, dict] = {}

        self._was_synchronizing: bool = False

    def on_status_message_received(self, msg: str) -> None:
        data = json.loads(msg)
        state = data.get("state")
        if state and "synchronizing" in state:
            synchronizing = state.get("synchronizing")
            self.synchronizing_state_changed.emit(synchronizing)
            if not self._was_synchronizing and synchronizing:
                self.sync_started.emit()
            elif self._was_synchronizing and not synchronizing:
                self.sync_stopped.emit()
            self._was_synchronizing = synchronizing

    @inlineCallbacks
    def do_check(self) -> TwistedDeferred[None]:
        folders = yield self.magic_folder.get_folders()
        for folder in folders:
            if folder not in self.folders:
                self.folder_added.emit(folder)
        for known_folder in self.folders:
            if known_folder not in folders:
                self.folder_removed.emit(known_folder)
        self.folders = folders

    def start(self) -> None:
        self.status_monitor.start()
        self.do_check()

    def stop(self) -> None:
        self.status_monitor.stop()


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
        self.monitor = MagicFolderMonitor(self)
        self.magic_folders: Dict[str, dict] = {}
        self.remote_magic_folders: Dict[str, dict] = {}
        self.backup_cap: str = ""

    @staticmethod
    def on_stdout_line_received(line: str) -> None:
        logging.debug("[magic-folder:stdout] %s", line)

    @staticmethod
    def on_stderr_line_received(line: str) -> None:
        logging.error("[magic-folder:stderr] %s", line)

    @staticmethod
    def on_log_line_received(line: str) -> None:
        logging.debug("[magic-folder:log] %s", line)

    @inlineCallbacks
    def _command(
        self, args: List[str], callback_trigger: str = ""
    ) -> TwistedDeferred[Union[Tuple[int, str], str]]:
        if not self.executable:
            self.executable = shutil.which("magic-folder")
        if not self.executable:
            raise EnvironmentError(
                'Could not find "magic-folder" executable on PATH.'
            )
        args = [
            self.executable,
            "--eliot-fd=2",  # redirect log output to stderr
            f"--config={self.configdir}",
        ] + args
        env = os.environ
        env["PYTHONUNBUFFERED"] = "1"
        logging.debug("Executing %s...", " ".join(args))
        protocol = SubprocessProtocol(
            callback_triggers=[callback_trigger],
            line_collectors={
                1: self.on_stdout_line_received,
                2: self.on_stderr_line_received,
            },
        )
        transport = yield reactor.spawnProcess(  # type: ignore
            protocol,
            self.executable,
            args=args,
            env=env,
            childFDs={1: "r", 2: "r"},
        )
        output = yield protocol.done  # type: ignore
        if callback_trigger:
            return transport.pid, output
        return output

    @inlineCallbacks
    def version(self) -> TwistedDeferred[str]:
        output = yield self._command(["--version"])
        return output

    def stop(self) -> None:
        self.monitor.stop()
        kill(pidfile=self.pidfile)

    @inlineCallbacks
    def _load_config(self) -> TwistedDeferred[None]:
        config_output = yield self._command(["show-config"])
        self.config = json.loads(config_output)
        self.api_token = self.config.get("api_token", "")
        if not self.api_token:
            raise MagicFolderError("Could not load magic-folder API token")

    @inlineCallbacks
    def _run(self) -> TwistedDeferred[Tuple[int, int]]:
        result = yield self._command(
            ["run"], "Completed initial Magic Folder setup"
        )
        pid, output = result
        port = 0
        for line in output.split("\n"):
            if "Site starting on " in line and not port:  # XXX
                try:
                    port = int(line.split(" ")[-1])
                except ValueError:
                    pass
        return (pid, port)

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
        result = yield self._run()
        self.pid, self.port = result
        self.pidfile.write_text(str(self.pid))
        yield self._load_config()
        self.monitor.start()

    @inlineCallbacks
    def await_running(self) -> TwistedDeferred[None]:
        while not self.monitor.status_monitor.running:  # XXX
            yield deferLater(reactor, 0.2, lambda: None)

    @inlineCallbacks
    def restart(self) -> TwistedDeferred[None]:
        logging.debug("Restarting magic-folder...")
        self.stop()
        yield self.start()
        logging.debug("Magic-folder restarted successfully")

    @inlineCallbacks
    def leave_folder(self, folder_name: str) -> TwistedDeferred[None]:
        yield self._command(
            [
                "leave",
                f"--name={folder_name}",
                "--really-delete-write-capability",
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
        if resp.code in (200, 201):
            return json.loads(content)
        raise MagicFolderWebError(
            f"Error {resp.code} requesting {method} /v1/{path}: {content}"
        )

    @inlineCallbacks
    def get_folders(self) -> TwistedDeferred[Dict[str, dict]]:
        folders = yield self._request(
            "GET", "/magic-folder?include_secret_information=1"
        )
        self.magic_folders = folders
        return folders

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
        data = {
            "name": name,
            "author_name": author,
            "local_path": str(p.resolve()),
            "poll_interval": str(poll_interval),
        }
        yield self._request(
            "POST", "/magic-folder", body=json.dumps(data).encode()
        )
        yield self.backup_folder(name)  # XXX

    @inlineCallbacks
    def get_snapshots(self) -> TwistedDeferred[Dict[str, dict]]:
        snapshots = yield self._request("GET", "/snapshot")
        return snapshots

    @inlineCallbacks
    def add_snapshot(
        self, folder_name: str, filepath: str
    ) -> TwistedDeferred[None]:
        try:
            magic_path = self.magic_folders[folder_name]["magic_path"]
        except KeyError:
            yield self.get_folders()
            magic_path = self.magic_folders[folder_name]["magic_path"]
        if filepath.startswith(magic_path):
            filepath = filepath[len(magic_path) + len(os.sep) :]
        yield self._request(
            "POST", f"/magic-folder/{folder_name}/snapshot?path={filepath}"
        )

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
    def create_backup_cap(self) -> TwistedDeferred[str]:
        yield self.gateway.lock.acquire()
        try:
            cap = yield self.gateway.mkdir(
                self.gateway.get_rootcap(), ".magic-folders"
            )
        finally:
            yield self.gateway.lock.release()
        return cap

    @inlineCallbacks
    def get_backup_cap(self) -> TwistedDeferred[str]:
        if self.backup_cap:
            return self.backup_cap
        rootcap = self.gateway.get_rootcap()
        yield self.gateway.await_ready()
        data = yield self.gateway.get_json(rootcap)
        try:
            self.backup_cap = data[1]["children"][".magic-folders"][1][
                "rw_uri"
            ]
        except (KeyError, TypeError):
            logging.debug("Magic-Folder backup cap not found; creating...")
            self.backup_cap = yield self.create_backup_cap()
            logging.debug("Magic-Folder backup cap successfully created")
        return self.backup_cap

    @inlineCallbacks
    def backup_folder(self, folder_name: str) -> TwistedDeferred[None]:
        folders = yield self.get_folders()
        data = folders.get(folder_name)
        collective_dircap = data.get("collective_dircap")
        upload_dircap = data.get("upload_dircap")
        backup_cap = yield self.get_backup_cap()
        yield self.gateway.link(
            backup_cap, f"{folder_name} (collective)", collective_dircap
        )
        yield self.gateway.link(
            backup_cap, f"{folder_name} (personal)", upload_dircap
        )

    @inlineCallbacks
    def get_remote_folders(self) -> TwistedDeferred[Dict[str, dict]]:
        folders: DefaultDict[str, dict] = defaultdict(dict)
        backup_cap = yield self.get_backup_cap()
        content = yield self.gateway.get_json(backup_cap)
        for name, data in content[1]["children"].items():
            data_dict = data[1]
            if name.endswith(" (collective)"):
                prefix = name.split(" (collective)")[0]
                folders[prefix]["collective_dircap"] = data_dict["ro_uri"]
            elif name.endswith(" (personal)"):
                prefix = name.split(" (personal)")[0]
                folders[prefix]["upload_dircap"] = data_dict["rw_uri"]
            elif name.endswith(" (admin)"):
                prefix = name.split(" (admin)")[0]
                folders[prefix]["admin_dircap"] = data_dict["rw_uri"]
        self.remote_magic_folders = folders
        return dict(folders)

    @inlineCallbacks
    def restore_folder(
        self, folder_name: str, local_path: str
    ) -> TwistedDeferred[None]:
        backup_cap = yield self.get_backup_cap()
        content = yield self.gateway.get_json(backup_cap)
        children = content[1]["children"]
        personal_metadata = children.get(f"{folder_name} (personal)")
        if not personal_metadata:
            raise MagicFolderWebError(
                f'Error restoring folder "{folder_name}"; '
                "personal metadata not found"
            )
        personal_dmd = personal_metadata[1]["ro_uri"]

        yield self.add_folder(local_path, randstr(8), name=folder_name)  # XXX
        author = f"Restored-{datetime.now().isoformat()}"
        yield self.add_participant(folder_name, author, personal_dmd)
