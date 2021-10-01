from __future__ import annotations

import json
import logging
import os
import shutil
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    DefaultDict,
    Deque,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

import treq
from PyQt5.QtCore import QObject, pyqtSignal
from twisted.internet import reactor
from twisted.internet.defer import DeferredList, inlineCallbacks
from twisted.internet.task import deferLater

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types import TwistedDeferred

from gridsync.crypto import randstr
from gridsync.system import SubprocessProtocol, kill
from gridsync.watchdog import Watchdog
from gridsync.websocket import WebSocketReaderService


class MagicFolderError(Exception):
    pass


class MagicFolderProcessError(MagicFolderError):
    pass


class MagicFolderWebError(MagicFolderError):
    pass


class MagicFolderMonitor(QObject):

    status_message_received = pyqtSignal(dict)

    sync_started = pyqtSignal(str)  # folder_name
    sync_stopped = pyqtSignal(str)  # folder_name

    folder_added = pyqtSignal(str)  # folder_name
    folder_removed = pyqtSignal(str)  # folder_name
    folder_mtime_updated = pyqtSignal(str, int)  # folder_name, mtime
    folder_size_updated = pyqtSignal(str, object)  # folder_name, size

    backup_added = pyqtSignal(str)  # folder_name
    backup_removed = pyqtSignal(str)  # folder_name

    file_added = pyqtSignal(str, dict)  # folder_name, status
    file_removed = pyqtSignal(str, dict)  # folder_name, status
    file_mtime_updated = pyqtSignal(str, dict)  # folder_name, status
    file_size_updated = pyqtSignal(str, dict)  # folder_name, status
    file_modified = pyqtSignal(str, dict)  # folder_name, status

    def __init__(self, magic_folder: MagicFolder) -> None:
        super().__init__()
        self.magic_folder = magic_folder

        self._ws_reader: Optional[WebSocketReaderService] = None
        self.running: bool = False
        self.syncing_folders: Set[str] = set()
        self.up_to_date: bool = False

        self._prev_state: Dict = {}
        self._known_folders: Dict[str, dict] = {}
        self._known_backups: List[str] = []
        self._prev_folders: Dict = {}

        self._watchdog = Watchdog()
        self._watchdog.path_modified.connect(self._schedule_magic_folder_scan)
        self._scheduled_scans: DefaultDict[str, set] = defaultdict(set)

    def _maybe_do_scan(self, event_id: str, path: str) -> None:
        try:
            self._scheduled_scans[path].remove(event_id)
        except KeyError:
            pass
        if self._scheduled_scans[path]:
            return
        for folder_name, data in self.magic_folder.magic_folders.items():
            magic_path = data.get("magic_path", "")
            if not magic_path:
                continue
            if path == magic_path or path.startswith(magic_path + os.sep):
                self.magic_folder.scan(folder_name)

    def _schedule_magic_folder_scan(self, path: str) -> None:
        event_id = randstr(8)
        self._scheduled_scans[path].add(event_id)
        reactor.callLater(0.25, lambda: self._maybe_do_scan(event_id, path))

    @staticmethod
    def _is_syncing(folder_name: str, folders_state: Dict) -> bool:
        folder_data = folders_state.get(folder_name)
        if not folder_data:
            return False
        if folder_data.get("uploads") or folder_data.get("downloads"):
            return True
        return False

    def compare_state(self, state: Dict) -> None:
        current_folders = state.get("folders", {})
        previous_folders = self._prev_state.get("folders", {})
        for folder in current_folders:
            is_syncing = self._is_syncing(folder, current_folders)
            was_syncing = self._is_syncing(folder, previous_folders)
            if is_syncing and not was_syncing:
                self.syncing_folders.add(folder)
                self.up_to_date = False
                self.sync_started.emit(folder)
            elif was_syncing and not is_syncing:
                try:
                    self.syncing_folders.remove(folder)
                except KeyError:
                    pass
                if not self.syncing_folders:
                    self.up_to_date = True
                self.sync_stopped.emit(folder)

    def compare_folders(self, folders: Dict[str, dict]) -> None:
        for folder, data in folders.items():
            if folder not in self._known_folders:
                self._watchdog.add_watch(data.get("magic_path", ""))
                self.folder_added.emit(folder)
        for folder, data in self._known_folders.items():
            if folder not in folders:
                self._watchdog.remove_watch(data.get("magic_path", ""))
                self.folder_removed.emit(folder)
        self._known_folders = folders

    def compare_backups(self, backups: List[str]) -> None:
        for backup in backups:
            if (
                backup not in self._known_backups
                and backup not in self._known_folders
            ):
                self.backup_added.emit(backup)
        for backup in self._known_backups:
            if backup not in backups:
                self.backup_removed.emit(backup)
        self._known_backups = list(backups)

    @staticmethod
    def _parse_file_status(
        file_status: List[Dict], magic_path: str
    ) -> Tuple[Dict[str, Dict], List[int], int, int]:
        files = {}
        sizes = []
        latest_mtime = 0
        for item in file_status:
            relpath = item.get("relpath", "")
            item["path"] = str(Path(magic_path, relpath).resolve())
            files[relpath] = item
            size = int(item.get("size", 0))
            sizes.append(size)
            mtime = item.get("last-updated", 0)
            if mtime > latest_mtime:
                latest_mtime = mtime
        total_size = sum(sizes)
        return files, sizes, total_size, latest_mtime

    def _compare_file_status(
        self,
        folder_name: str,
        magic_path: str,
        file_status: List[Dict],
        previous_file_status: List[Dict],
    ) -> None:
        current = self._parse_file_status(file_status, magic_path)
        current_files, _, current_total_size, current_latest_mtime = current
        previous = self._parse_file_status(previous_file_status, magic_path)
        prev_files, _, prev_total_size, prev_latest_mtime = previous

        for file, status in current_files.items():
            if file not in prev_files:
                self.file_added.emit(folder_name, status)
            else:
                prev_status = prev_files.get(file, {})
                prev_size = prev_status.get("size", 0)
                prev_mtime = prev_status.get("mtime", 0)
                size = status.get("size")
                mtime = status.get("mtime")
                modified = False
                if mtime != prev_mtime:
                    modified = True
                    self.file_mtime_updated.emit(folder_name, status)
                if size != prev_size:
                    modified = True
                    self.file_size_updated.emit(folder_name, status)
                if modified:
                    self.file_modified.emit(folder_name, status)
        for file, status in prev_files.items():
            if file not in prev_files:
                self.file_removed.emit(folder_name, status)
        if current_total_size != prev_total_size:
            self.folder_size_updated.emit(folder_name, current_total_size)
        if current_latest_mtime != prev_latest_mtime:
            self.folder_mtime_updated.emit(folder_name, current_latest_mtime)

    def compare_files(self, folders: Dict) -> None:
        for folder_name, data in folders.items():
            self._compare_file_status(
                folder_name,
                data.get("magic_path", ""),
                data.get("file_status", []),
                self._prev_folders.get(folder_name, {}).get("file_status", []),
            )

    def on_status_message_received(self, msg: str) -> None:
        data = json.loads(msg)
        self.status_message_received.emit(data)
        state = data.get("state")
        self.compare_state(state)
        self._prev_state = state
        self.do_check()  # XXX

    @inlineCallbacks
    def _get_file_status(self, folder_name: str) -> TwistedDeferred[Tuple]:
        result = yield self.magic_folder.get_file_status(folder_name)
        return (folder_name, result)

    @inlineCallbacks
    def do_check(self) -> TwistedDeferred[None]:
        folders = yield self.magic_folder.get_folders()
        self.compare_folders(folders)
        folder_backups = yield self.magic_folder.get_folder_backups()
        self.compare_backups(list(folder_backups))
        results = yield DeferredList(
            [self._get_file_status(f) for f in folders]
        )
        for success, result in results:
            if success:  # XXX
                folder_name, file_status = result
                folders[folder_name]["file_status"] = file_status
        self.compare_files(folders)
        self._prev_folders = folders

    def start(self) -> None:
        self._ws_reader = WebSocketReaderService(
            f"ws://127.0.0.1:{self.magic_folder.port}/v1/status",
            headers={"Authorization": f"Bearer {self.magic_folder.api_token}"},
            collector=self.on_status_message_received,
        )
        self._ws_reader.start()
        self._watchdog.start()
        self.running = True
        self.do_check()

    def stop(self) -> None:
        self.running = False
        self._watchdog.stop()
        if self._ws_reader:
            self._ws_reader.stop()
            self._ws_reader = None


class MagicFolder:
    def __init__(
        self,
        gateway: Tahoe,
        executable: Optional[str] = "",
        logs_maxlen: Optional[int] = 1000000,
    ) -> None:
        self.gateway = gateway
        self.executable = executable
        self._log_buffer: Deque[bytes] = deque(maxlen=logs_maxlen)

        self.configdir = Path(gateway.nodedir, "private", "magic-folder")
        self.pidfile = Path(self.configdir, "magic-folder.pid")
        self.pid: int = 0
        self.port: int = 0
        self.config: dict = {}
        self.api_token: str = ""
        self.monitor = MagicFolderMonitor(self)
        self.magic_folders: Dict[str, dict] = {}
        self.remote_magic_folders: Dict[str, dict] = {}
        self.rootcap_manager = gateway.rootcap_manager

    @staticmethod
    def on_stdout_line_received(line: str) -> None:
        logging.debug("[magic-folder:stdout] %s", line)

    @staticmethod
    def _is_eliot_log_message(s: str) -> bool:
        try:
            data = json.loads(s)
        except json.decoder.JSONDecodeError:
            return False
        if (
            isinstance(data, dict)
            and "timestamp" in data
            and "task_uuid" in data
        ):
            return True
        return False

    def on_stderr_line_received(self, line: str) -> None:
        if self._is_eliot_log_message(line):
            self._log_buffer.append(line.encode("utf-8"))
        else:
            logging.error("[magic-folder:stderr] %s", line)

    def get_log_messages(self) -> list:
        return list(msg.decode("utf-8") for msg in list(self._log_buffer))

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
            stdout_line_collector=self.on_stdout_line_received,
            stderr_line_collector=self.on_stderr_line_received,
        )
        transport = yield reactor.spawnProcess(  # type: ignore
            protocol, self.executable, args=args, env=env
        )
        output = yield protocol.done
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
        logging.debug("Started magic-folder")

    @inlineCallbacks
    def await_running(self) -> TwistedDeferred[None]:
        while not self.monitor.running:  # XXX
            yield deferLater(reactor, 0.2, lambda: None)  # type: ignore

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
            f"Error {resp.code} requesting {method} /v1{path}: {content}"
        )

    @inlineCallbacks
    def get_folders(self) -> TwistedDeferred[Dict[str, dict]]:
        folders = yield self._request(
            "GET", "/magic-folder?include_secret_information=1"
        )
        self.magic_folders = folders
        return folders

    @inlineCallbacks
    def add_folder(  # pylint: disable=too-many-arguments
        self,
        path: str,
        author: str,
        name: Optional[str] = "",
        poll_interval: int = 60,
        scan_interval: int = 60,
    ) -> TwistedDeferred[None]:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if not name:
            name = p.name
        data = {
            "name": name,
            "author_name": author,
            "local_path": str(p.resolve()),
            "poll_interval": poll_interval,
            "scan_interval": scan_interval,
        }
        yield self._request(
            "POST", "/magic-folder", body=json.dumps(data).encode()
        )
        yield self.create_folder_backup(name)  # XXX

    @inlineCallbacks
    def leave_folder(self, folder_name: str) -> TwistedDeferred[None]:
        yield self._request(
            "DELETE",
            f"/magic-folder/{folder_name}",
            body=json.dumps({"really-delete-write-capability": True}).encode(),
        )

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
    def get_file_status(self, folder_name: str) -> TwistedDeferred[List[Dict]]:
        output = yield self._request(
            "GET", f"/magic-folder/{folder_name}/file-status"
        )
        return output

    @inlineCallbacks
    def get_object_sizes(self, folder_name: str) -> TwistedDeferred[List[int]]:
        # XXX A placeholder for now...
        # See https://github.com/LeastAuthority/magic-folder/pull/528
        sizes = []
        file_status = yield self.get_file_status(folder_name)
        for item in file_status:
            # Include size of content, snapshot cap, and metadata cap
            sizes.extend([item.get("size", 0), 420, 184])
        return sizes

    @inlineCallbacks
    def get_all_object_sizes(self) -> TwistedDeferred[List[int]]:
        all_sizes = []
        folders = yield self.get_folders()
        for folder in folders:
            sizes = yield self.get_object_sizes(folder)
            all_sizes.extend(sizes)
        return all_sizes

    @inlineCallbacks
    def scan(self, folder_name: str) -> TwistedDeferred[Dict]:
        output = yield self._request(
            "PUT",
            f"/magic-folder/{folder_name}/scan",
            body=json.dumps({"wait-for-snapshots": True}).encode("utf-8"),
        )
        return output

    @inlineCallbacks
    def create_folder_backup(self, folder_name: str) -> TwistedDeferred[None]:
        folders = yield self.get_folders()
        data = folders.get(folder_name)
        collective_dircap = data.get("collective_dircap")
        upload_dircap = data.get("upload_dircap")
        yield self.rootcap_manager.add_backup(
            ".magic-folders", f"{folder_name} (collective)", collective_dircap
        )
        yield self.rootcap_manager.add_backup(
            ".magic-folders", f"{folder_name} (personal)", upload_dircap
        )

    @inlineCallbacks
    def get_folder_backups(self) -> TwistedDeferred[Dict[str, dict]]:
        folders: DefaultDict[str, dict] = defaultdict(dict)
        backups = yield self.rootcap_manager.get_backups(".magic-folders")
        for name, data in backups.items():
            if name.endswith(" (collective)"):
                prefix = name.split(" (collective)")[0]
                folders[prefix]["collective_dircap"] = data.get("cap")
            elif name.endswith(" (personal)"):
                prefix = name.split(" (personal)")[0]
                folders[prefix]["upload_dircap"] = data.get("cap")
        self.remote_magic_folders = folders
        return dict(folders)

    @inlineCallbacks
    def remove_folder_backup(self, folder_name: str) -> TwistedDeferred[None]:
        yield DeferredList(
            [
                self.rootcap_manager.remove_backup(
                    ".magic-folders", folder_name + " (collective)"
                ),
                self.rootcap_manager.remove_backup(
                    ".magic-folders", folder_name + " (personal)"
                ),
            ]
        )

    @inlineCallbacks
    def restore_folder_backup(
        self, folder_name: str, local_path: str
    ) -> TwistedDeferred[None]:
        backups = yield self.get_folder_backups()
        data = backups.get(folder_name, {})
        upload_dircap = data.get("upload_dircap")
        personal_dmd = yield self.gateway.diminish(upload_dircap)
        yield self.add_folder(local_path, randstr(8), name=folder_name)  # XXX
        author = f"Restored-{datetime.now().isoformat()}"
        yield self.add_participant(folder_name, author, personal_dmd)
