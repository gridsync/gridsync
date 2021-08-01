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

    mtime_updated = pyqtSignal(str, int)  # folder_name, mtime
    size_updated = pyqtSignal(str, object)  # folder_name, size

    file_added = pyqtSignal(str, dict)  # folder_name, status
    file_removed = pyqtSignal(str, dict)  # folder_name, status
    file_modified = pyqtSignal(str, dict)  # folder_name, status

    def __init__(self, magic_folder: MagicFolder) -> None:
        super().__init__()
        self.magic_folder = magic_folder

        self._ws_reader: Optional[WebSocketReaderService] = None
        self.running: bool = False
        self.syncing_folders: Set[str] = set()
        self.up_to_date: bool = False

        self._prev_state: Dict = {}
        self._known_folders: List[str] = []
        self._prev_folders: Dict = {}

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
                print("*** STARTED SYNCING:", folder)
                self.syncing_folders.add(folder)
                self.up_to_date = False
                self.sync_started.emit(folder)
            elif was_syncing and not is_syncing:
                print("*** STOPPED SYNCING:", folder)
                try:
                    self.syncing_folders.remove(folder)
                except KeyError:
                    pass
                if not self.syncing_folders:
                    self.up_to_date = True
                self.sync_stopped.emit(folder)

    def compare_folders(self, folders: List[str]) -> None:
        for folder in folders:
            if folder not in self._known_folders:
                self.folder_added.emit(folder)
        for folder in self._known_folders:
            if folder not in folders:
                self.folder_removed.emit(folder)
        self._known_folders = list(folders)

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
            # XXX Magic-Folder's status API reveals nothing about when
            # files were added/modified/removed/restored to a *remote*
            # snapshot/DMD so, for now, use the "last-updated" value
            # (which corresponds to the timestamp of the *local*
            # snapshot). This is not ideal since what really matters to
            # users, presumably, is whether and when their files were
            # actually stored *on the grid*; users probably don't need
            # to care -- or even known about the existence of -- local
            # snapshots at all (given that they already have local
            # copies of the files to which those snapshots correspond).
            # (Note that the Magic-Folder status API also provides an
            # "mtime" value, but this corresponds to the mtime returned
            # by the stat() syscall and isn't what we want either.)
            # mtime = item.get("mtime", 0)
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
        current_files, _, current_size, current_mtime = current
        previous = self._parse_file_status(previous_file_status, magic_path)
        prev_files, _, prev_size, prev_mtime = previous

        for file, status in current_files.items():
            if file not in prev_files:
                print("*** FILE_ADDED: ", folder_name, status)
                self.file_added.emit(folder_name, status)
            else:
                prev_status = prev_files.get(file, {})
                prev_size = prev_status.get("size", 0)
                prev_mtime = prev_status.get("mtime", 0)
                size = status.get("size")
                mtime = status.get("mtime")
                if size != prev_size or mtime != prev_mtime:
                    print("*** FILE_MODIFIED: ", folder_name, status)
                    self.file_modified.emit(folder_name, status)
        for file, status in prev_files.items():
            if file not in prev_files:
                print("*** FILE REMOVED: ", folder_name, status)
                self.file_removed.emit(folder_name, status)

        print("### current_size", current_size)
        print("### prev_size", prev_size)
        if current_size != prev_size:
            print("*** SIZE UPDATED: ", folder_name, current_size)
            self.size_updated.emit(folder_name, current_size)

        print("@@@ current_mtime", current_mtime)
        print("@@@ prev_mtime", prev_mtime)
        if current_mtime != prev_mtime:
            print("*** MTIME UPDATED: ", folder_name, current_mtime)
            self.mtime_updated.emit(folder_name, current_mtime)

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
        from pprint import pprint

        pprint(data)
        self.status_message_received.emit(data)
        state = data.get("state")
        folders = state.get("folders")
        self.compare_folders(list(folders))
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
        self.running = True
        self.do_check()

    def stop(self) -> None:
        self.running = False
        if self._ws_reader:
            self._ws_reader.stop()
            self._ws_reader = None


class MagicFolder:
    def __init__(
        self,
        gateway: Tahoe,
        executable: Optional[str] = "",
        logs_maxlen: int = 1000000,  # XXX
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
        self.backup_cap: str = ""

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
        # Because it is better to waste computing resources than to
        # waste users' time (and Magic-Folder is slow enough as-is...).
        # See: https://github.com/LeastAuthority/magic-folder/issues/513
        poll_interval: int = 3,  # XXX Magic-Folder defaults to 60
        scan_interval: int = 3,  # XXX Magic-Folder defaults to 60
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
    def scan(self, folder_name: str) -> TwistedDeferred[Dict]:
        output = yield self._request(
            "PUT",
            f"/magic-folder/{folder_name}/scan",
            body=json.dumps({"wait-for-snapshots": True}).encode("utf-8"),
        )
        return output

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
    def create_folder_backup(self, folder_name: str) -> TwistedDeferred[None]:
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
    def get_folder_backups(self) -> TwistedDeferred[Dict[str, dict]]:
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
    def restore_folder_backup(
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
