from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union, cast

import treq
from qtpy.QtCore import QObject, Signal
from twisted.internet import reactor
from twisted.internet.defer import Deferred, DeferredList
from twisted.internet.error import ConnectionRefusedError as ConnectionRefused
from twisted.internet.task import deferLater

if TYPE_CHECKING:
    from gridsync.tahoe import Tahoe  # pylint: disable=cyclic-import
    from gridsync.types_ import JSON

from gridsync import APP_NAME
from gridsync.capabilities import diminish
from gridsync.crypto import randstr
from gridsync.filter import is_eliot_log_message
from gridsync.log import MultiFileLogger, NullLogger
from gridsync.magic_folder_events import (
    MagicFolderEventHandler,
    MagicFolderEventsMonitor,
    MagicFolderStatus,
)
from gridsync.msg import critical
from gridsync.supervisor import Supervisor
from gridsync.system import SubprocessProtocol, which
from gridsync.watchdog import Watchdog


class MagicFolderError(Exception):
    pass


class MagicFolderConfigError(MagicFolderError):
    pass


class MagicFolderProcessError(MagicFolderError):
    pass


class MagicFolderWebError(MagicFolderError):
    def __init__(
        self, message: str, code: int | None = None, reason: str | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reason = reason


class MagicFolderWatchdog:
    def __init__(self, magic_folder: MagicFolder) -> None:
        self.magic_folder = magic_folder

        self._scheduled_scans: defaultdict[str, set] = defaultdict(set)
        self._watchdog = Watchdog()
        self._watchdog.path_modified.connect(self._schedule_scan)

    def _maybe_do_scan(self, event_id: str, path: str) -> None:
        # TODO: Don't scan if sync is in progress?
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
                # XXX Something should handle errors
                Deferred.fromCoroutine(self.magic_folder.scan(folder_name))

    def _schedule_scan(self, path: str) -> None:
        event_id = randstr(16)
        self._scheduled_scans[path].add(event_id)
        reactor.callLater(  # type: ignore
            0.25, lambda: self._maybe_do_scan(event_id, path)
        )

    def add_watch(self, path: str) -> None:
        try:
            self._watchdog.add_watch(path)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("Error adding watch for %s: %s", path, str(exc))

    def remove_watch(self, path: str) -> None:
        try:
            self._watchdog.remove_watch(path)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("Error removing watch for %s: %s", path, str(exc))

    def stop(self) -> None:
        self._watchdog.stop()

    def start(self) -> None:
        self._watchdog.start()


class MagicFolderMonitor(QObject):
    folder_mtime_updated = Signal(str, int)  # folder_name, mtime
    folder_size_updated = Signal(str, object)  # folder_name, size

    backup_added = Signal(str)  # folder_name
    backup_removed = Signal(str)  # folder_name

    file_added = Signal(str, dict)  # folder_name, status
    file_removed = Signal(str, dict)  # folder_name, status
    file_mtime_updated = Signal(str, dict)  # folder_name, status
    file_size_updated = Signal(str, dict)  # folder_name, status
    file_modified = Signal(str, dict)  # folder_name, status

    total_folders_size_updated = Signal(object)  # "object" avoids overflows

    def __init__(self, magic_folder: MagicFolder) -> None:
        super().__init__()
        self.magic_folder = magic_folder

        self.running: bool = False

        self._known_folders: dict[str, dict] = {}
        self._known_backups: list[str] = []

        self._folder_sizes: dict[str, int] = {}
        self._total_folders_size: int = 0

        self._watchdog = MagicFolderWatchdog(self.magic_folder)

        self.event_handler = MagicFolderEventHandler()
        self.events_monitor = MagicFolderEventsMonitor(self.event_handler)

        self.event_handler.folder_added.connect(
            lambda _: Deferred.fromCoroutine(self.do_check())
        )
        self.event_handler.folder_removed.connect(
            lambda _: Deferred.fromCoroutine(self.do_check())
        )
        self.event_handler.folder_status_changed.connect(
            lambda f, s: Deferred.fromCoroutine(self.do_check())
        )

    def compare_folders(
        self,
        current_folders: dict[str, dict],
        previous_folders: dict[str, dict],
    ) -> None:
        for folder, data in current_folders.items():
            if folder not in previous_folders:
                # Magic-Folder does not send "folder-added" events for
                # already-existing folders on startup, so manually emit
                # the signal when we first see a folder.
                self.event_handler.folder_added.emit(folder)  # XXX
                magic_path = data.get("magic_path", "")
                self._watchdog.add_watch(magic_path)
        for folder, data in previous_folders.items():
            if folder not in current_folders:
                magic_path = data.get("magic_path", "")
                self._watchdog.remove_watch(magic_path)

    def compare_backups(
        self, current_backups: list[str], previous_backups: list[str]
    ) -> None:
        for backup in current_backups:
            if (
                backup not in previous_backups
                and backup not in self._known_folders  # XXX
            ):
                self.backup_added.emit(backup)
        for backup in previous_backups:
            if backup not in current_backups:
                self.backup_removed.emit(backup)

    @staticmethod
    def _parse_file_status(
        file_status: list[dict], magic_path: str
    ) -> tuple[dict[str, dict], list[int], int, int]:
        files = {}
        sizes = []
        latest_mtime = 0
        for item in file_status:
            relpath = item.get("relpath", "")
            item["path"] = str(Path(magic_path, relpath).resolve())
            files[relpath] = item
            size = int(item.get("size") or 0)  # XXX "size" is None if deleted
            sizes.append(size)
            mtime = item.get("last-updated", 0)
            latest_mtime = max(latest_mtime, mtime)
        total_size = sum(sizes)
        return files, sizes, total_size, latest_mtime

    def _compare_file_status(
        self,
        folder_name: str,
        magic_path: str,
        file_status: list[dict],
        previous_file_status: list[dict],
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

        self._folder_sizes[folder_name] = current_total_size

    def _check_total_folders_size(self) -> None:
        total = sum(self._folder_sizes.values())
        if total != self._total_folders_size:
            self._total_folders_size = total
            self.total_folders_size_updated.emit(total)

    def compare_files(
        self, current_folders: dict, previous_folders: dict
    ) -> None:
        for folder_name, data in current_folders.items():
            self._compare_file_status(
                folder_name,
                data.get("magic_path", ""),
                data.get("file_status", []),
                previous_folders.get(folder_name, {}).get("file_status", []),
            )
        self._check_total_folders_size()

    async def _get_file_status(
        self, folder_name: str
    ) -> tuple[str, list[dict]]:
        result = await self.magic_folder.get_file_status(folder_name)
        return (folder_name, result)

    async def do_check(self) -> None:
        folders = await self.magic_folder.get_folders()
        current_folders = dict(folders)
        previous_folders = dict(self._known_folders)
        self.compare_folders(current_folders, previous_folders)
        self._known_folders = current_folders

        backups = await self.magic_folder.get_folder_backups()
        if backups is None:
            logging.warning("Could not read Magic-Folder backups during check")
        else:
            current_backups = list(backups)
            previous_backups = list(self._known_backups)
            self.compare_backups(current_backups, previous_backups)
            self._known_backups = current_backups

        results = await DeferredList(
            [
                Deferred.fromCoroutine(self._get_file_status(f))
                for f in current_folders
            ],
            consumeErrors=True,
        )
        for success, result in results:
            if success:  # XXX
                folder_name, file_status = result
                current_folders[folder_name]["file_status"] = file_status
        self.compare_files(current_folders, previous_folders)
        self._known_folders = current_folders

    def start(self) -> None:
        self.events_monitor.start(
            self.magic_folder.api_port, self.magic_folder.api_token
        )
        self._watchdog.start()
        self.running = True
        # XXX Something should wait on the result
        Deferred.fromCoroutine(self.do_check())

    def stop(self) -> None:
        self.running = False
        self._watchdog.stop()
        self.events_monitor.stop()


class MagicFolder:
    def __init__(
        self,
        gateway: Tahoe,
        executable: Optional[str] = "",
        enable_logging: bool = True,
    ) -> None:
        self.gateway = gateway
        self.executable = executable

        self.configdir = Path(gateway.nodedir, "private", "magic-folder")
        self.api_port: int = 0
        self.api_token: str = ""
        self.monitor = MagicFolderMonitor(self)
        self.events = self.monitor.event_handler  # XXX
        self.magic_folders: dict[str, dict] = {}
        self.remote_magic_folders: dict[str, dict] = {}
        self.rootcap_manager = gateway.rootcap_manager
        self.supervisor: Supervisor = Supervisor(
            Path(self.configdir) / "running.process",
        )

        self.logger: Union[MultiFileLogger, NullLogger]
        if enable_logging:
            self.logger = MultiFileLogger(f"{gateway.name}.Magic-Folder")
        else:
            self.logger = NullLogger()

    def on_stdout_line_received(self, line: str) -> None:
        self.logger.log("stdout", line)

    def on_stderr_line_received(self, line: str) -> None:
        if is_eliot_log_message(line):
            line = json.dumps(json.loads(line), sort_keys=True)
            self.logger.log("eliot", line, omit_fmt=True)
        else:
            self.logger.log("stderr", line)

    def get_log(self, name: str) -> str:
        return self.logger.read_log(name)

    def _base_command_args(self) -> list[str]:
        if not self.executable:
            self.executable = which("magic-folder")
        # Redirect/write eliot logs to stderr
        return [self.executable, "--eliot-fd=2", f"--config={self.configdir}"]

    async def _command(self, args: list[str]) -> str:
        args = self._base_command_args() + args
        logging.debug("Executing %s...", " ".join(args))
        os.environ["PYTHONUNBUFFERED"] = "1"
        protocol = SubprocessProtocol(
            stdout_line_collector=self.on_stdout_line_received,
            stderr_line_collector=self.on_stderr_line_received,
        )
        reactor.spawnProcess(  # type: ignore
            protocol, self.executable, args=args
        )
        output = await protocol.done
        return output

    async def version(self) -> str:
        output = await self._command(["--version"])
        return output.lstrip("Magic Folder version ")

    async def stop(self) -> None:
        self.monitor.stop()
        await self.supervisor.stop()

    def _read_api_token(self) -> str:
        p = Path(self.configdir, "api_token")
        try:
            api_token = p.read_text(encoding="utf-8").strip()
        except OSError as e:
            raise MagicFolderConfigError(
                f"Error reading {p.name}: {str(e)}"
            ) from e
        return api_token

    def _read_api_port(self) -> int:
        p = Path(self.configdir, "api_client_endpoint")
        try:
            api_client_endpoint = p.read_text(encoding="utf-8").strip()
        except OSError as e:
            raise MagicFolderConfigError(
                f"Error reading {p.name}: {str(e)}"
            ) from e
        if api_client_endpoint == "not running":
            raise MagicFolderError(
                "API endpoint is not available; Magic-Folder is not running"
            )
        try:
            port = int(api_client_endpoint.split(":")[-1])
        except ValueError as e:
            raise MagicFolderConfigError(
                f"Error parsing API port: {str(e)}"
            ) from e
        return port

    def _on_started(self) -> None:
        self.api_token = self._read_api_token()
        self.api_port = self._read_api_port()
        self.monitor.start()

    async def start(self) -> None:
        logging.debug("Starting magic-folder...")
        if not self.configdir.exists():
            await self._command(
                [
                    "init",
                    "-l",
                    "tcp:0:interface=127.0.0.1",
                    "-n",
                    self.gateway.nodedir,
                ]
            )
        try:
            await self.supervisor.start(
                self._base_command_args() + ["run"],
                started_trigger="Completed initial Magic Folder setup",
                stdout_line_collector=self.on_stdout_line_received,
                stderr_line_collector=self.on_stderr_line_received,
                call_after_start=self._on_started,
            )
        except Exception as exc:  # pylint: disable=broad-except
            critical(
                "Error starting Magic-Folder",
                "A critical error occurred when attempting to start a "
                f"Magic-Folder subprocess for {self.gateway.name}. {APP_NAME} "
                'will now exit.\n\nClick "Show Details..." for more '
                "information.",
                str(exc),
            )
        logging.debug("Started magic-folder")

    async def await_running(self) -> None:
        while not self.monitor.running:  # XXX
            await deferLater(reactor, 0.2, lambda: None)  # type: ignore

    async def _request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        error_404_ok: bool = False,
    ) -> JSON:
        await self.await_running()  # XXX
        if not self.api_token:
            raise MagicFolderWebError("API token not found")
        if not self.api_port:
            raise MagicFolderWebError("API port not found")
        try:
            resp = await treq.request(
                method,
                f"http://127.0.0.1:{self.api_port}{path}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                data=body,
            )
        except (ConnectionRefusedError, ConnectionRefused):
            self.api_port = self._read_api_port()
            resp = await treq.request(
                method,
                f"http://127.0.0.1:{self.api_port}{path}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                data=body,
            )
        if resp.code == 401:
            # From https://github.com/LeastAuthority/magic-folder/blob/
            # main/docs/interface.rst: "The token value is periodically
            # rotated so clients must be prepared to receive an
            # Unauthorized response even when supplying the token. In
            # this case, the client should re-read the token from the
            # filesystem to determine if the value held in memory has
            # become stale."
            self.api_token = self._read_api_token()
            resp = await treq.request(
                method,
                f"http://127.0.0.1:{self.api_port}{path}",
                headers={"Authorization": f"Bearer {self.api_token}"},
                data=body,
            )
        content = await treq.content(resp)
        try:
            json_content = json.loads(content)
        except json.JSONDecodeError:
            json_content = None
        if json_content is not None:
            try:
                reason = json_content.get("reason")
            except Exception:  # pylint: disable=broad-except
                reason = None
        else:
            reason = None
        if resp.code in (200, 201) or (resp.code == 404 and error_404_ok):
            return json_content
        raise MagicFolderWebError(
            f"Error {resp.code} requesting {method} {path}: {str(content)}",
            code=resp.code,
            reason=reason,
        )

    async def get_folders(self) -> dict[str, dict]:
        folders = await self._request(
            "GET", "/v1/magic-folder?include_secret_information=1"
        )
        if isinstance(folders, dict):
            self.magic_folders = folders
            return folders

        raise TypeError(
            f"Expected folders as dict, instead got {type(folders)!r}"
        )

    async def write_collective_dircap(
        self, folder_name: str, cap: str
    ) -> None:
        folders = await self.get_folders()
        stash_path = folders.get(folder_name, {}).get("stash_path", "")
        if not stash_path:
            raise FileNotFoundError(
                f"Magic-Folder stash path missing for {folder_name}"
            )
        state_db = Path(Path(stash_path).parent, "state.sqlite")
        if not state_db.exists():
            raise FileNotFoundError(
                f"Magic-Folder state database not found for {folder_name}"
            )
        connection = sqlite3.connect(state_db)
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION")
        cursor.execute("UPDATE [config] SET collective_dircap=?", (cap,))
        connection.commit()

    @property
    def wormhole_uri(self) -> str:
        global_db = Path(self.configdir, "global.sqlite")
        connection = sqlite3.connect(global_db)
        cursor = connection.cursor()
        cursor.execute("SELECT wormhole_uri FROM config")
        return cursor.fetchone()[0]

    @wormhole_uri.setter
    def wormhole_uri(self, uri: str) -> None:
        global_db = Path(self.configdir, "global.sqlite")
        connection = sqlite3.connect(global_db)
        cursor = connection.cursor()
        cursor.execute("BEGIN IMMEDIATE TRANSACTION")
        cursor.execute("UPDATE config SET wormhole_uri=?", (uri,))
        connection.commit()

    async def add_folder(  # pylint: disable=too-many-arguments
        self,
        path: str,
        author: str,
        name: Optional[str] = "",
        poll_interval: int = 60,
        scan_interval: int = 60,
    ) -> None:
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
        await self._request(
            "POST", "/v1/magic-folder", body=json.dumps(data).encode()
        )
        await self.create_folder_backup(name)  # XXX

    async def leave_folder(
        self, folder_name: str, missing_ok: bool = False
    ) -> None:
        await self._request(
            "DELETE",
            f"/v1/magic-folder/{folder_name}",
            body=json.dumps({"really-delete-write-capability": True}).encode(),
            error_404_ok=missing_ok,
        )
        try:
            del self.magic_folders[folder_name]
        except KeyError:
            pass

    def get_directory(self, folder_name: str) -> str:
        return self.magic_folders.get(folder_name, {}).get("magic_path", "")

    def get_status(self, folder_name: str) -> MagicFolderStatus:
        return self.events.operations_monitor.get_status(folder_name)  # XXX

    def folder_is_local(self, folder_name: str) -> bool:
        return bool(folder_name in self.magic_folders)

    def folder_is_remote(self, folder_name: str) -> bool:
        return bool(folder_name in self.remote_magic_folders)

    def folder_exists(self, folder_name: str) -> bool:
        return bool(
            self.folder_is_local(folder_name)
            or self.folder_is_remote(folder_name)
        )

    def is_admin(self, folder_name: str) -> bool:
        return self.magic_folders.get(folder_name, {}).get("is_admin", False)

    async def get_participants(self, folder_name: str) -> dict[str, dict]:
        participants = await self._request(
            "GET", f"/v1/magic-folder/{folder_name}/participants"
        )
        if isinstance(participants, dict):
            return participants
        raise TypeError(
            f"Expected participants as dict, instead got {type(participants)!r}"
        )

    async def add_participant(
        self, folder_name: str, author_name: str, personal_dmd: str
    ) -> None:
        data = {"author": {"name": author_name}, "personal_dmd": personal_dmd}
        await self._request(
            "POST",
            f"/v1/magic-folder/{folder_name}/participants",
            body=json.dumps(data).encode("utf-8"),
        )

    async def get_file_status(self, folder_name: str) -> list[dict]:
        output = await self._request(
            "GET", f"/v1/magic-folder/{folder_name}/file-status"
        )
        if isinstance(output, list):
            return output
        raise TypeError(
            f"Expected file status as a list, instead got {type(output)!r}"
        )

    async def get_object_sizes(self, folder_name: str) -> list[int]:
        sizes = await self._request(
            "GET", f"/v1/magic-folder/{folder_name}/tahoe-objects"
        )
        if isinstance(sizes, list):
            # XXX The magic-folder API should most likely return this list as
            # a property of an object.
            return sizes
        raise TypeError(
            f"Expected object sizes as list, instead got {type(sizes)!r}"
        )

    async def get_all_object_sizes(self) -> list[int]:
        all_sizes = []
        folders = await self.get_folders()
        for folder in folders:
            sizes = await self.get_object_sizes(folder)
            all_sizes.extend(sizes)
        return all_sizes

    async def scan(self, folder_name: str) -> dict:
        output = await self._request(
            "PUT",
            f"/v1/magic-folder/{folder_name}/scan-local",
            error_404_ok=True,
        )
        if isinstance(output, dict):
            return output
        raise TypeError(
            f"Expected scan result as dict, instead got {type(output)!r}"
        )

    async def poll(self, folder_name: str) -> dict:
        output = await self._request(
            "PUT",
            f"/v1/magic-folder/{folder_name}/poll-remote",
            error_404_ok=True,
        )
        if isinstance(output, dict):
            return output
        raise TypeError(
            f"Expected poll remote result as dict, instead got {type(output)!r}"
        )

    async def create_folder_backup(self, folder_name: str) -> None:
        folders = await self.get_folders()
        data = folders.get(folder_name)
        if data is None:
            raise ValueError("Folder is missing from folder data")
        collective_dircap = data.get("collective_dircap")
        upload_dircap = data.get("upload_dircap")
        if collective_dircap is None:
            raise ValueError("Collective dircap in folder data is missing")
        if upload_dircap is None:
            raise ValueError("Upload dircap in folder data is missing")
        await self.rootcap_manager.add_backup(
            ".magic-folders",
            f"{folder_name} (collective)",
            collective_dircap,
        )
        await self.rootcap_manager.add_backup(
            ".magic-folders", f"{folder_name} (personal)", upload_dircap
        )

    async def get_folder_backups(self) -> Optional[dict[str, dict]]:
        folders: defaultdict[str, dict] = defaultdict(dict)
        backups = await self.rootcap_manager.get_backups(".magic-folders")
        if backups is None:
            return None
        for name, data in backups.items():
            if name.endswith(" (collective)"):
                prefix = name.split(" (collective)")[0]
                folders[prefix]["collective_dircap"] = data.get("cap")
            elif name.endswith(" (personal)"):
                prefix = name.split(" (personal)")[0]
                folders[prefix]["upload_dircap"] = data.get("cap")
        self.remote_magic_folders = folders
        return dict(folders)

    async def remove_folder_backup(self, folder_name: str) -> None:
        await DeferredList(
            [
                Deferred.fromCoroutine(
                    self.rootcap_manager.remove_backup(
                        ".magic-folders", folder_name + " (collective)"
                    )
                ),
                Deferred.fromCoroutine(
                    self.rootcap_manager.remove_backup(
                        ".magic-folders", folder_name + " (personal)"
                    )
                ),
            ]
        )
        try:
            del self.remote_magic_folders[folder_name]
        except KeyError:
            pass

    async def restore_folder_backup(
        self, folder_name: str, local_path: str
    ) -> None:
        logging.debug('Restoring "%s" Magic-Folder...', folder_name)
        backups = await self.get_folder_backups()
        if backups is None:
            raise MagicFolderError(
                f"Error restoring folder {folder_name}; could not read backups"
            )
        data = backups.get(folder_name, {})
        upload_dircap = data.get("upload_dircap")
        if upload_dircap is None:
            raise ValueError("Upload directory cap missing from folder backup")
        personal_dmd = diminish(upload_dircap)
        await self.add_folder(local_path, randstr(8), name=folder_name)  # XXX
        author = f"Restored-{datetime.now().isoformat()}"
        await self.add_participant(folder_name, author, personal_dmd)
        logging.debug('Successfully restored "%s" Magic-Folder', folder_name)
        await self.poll(folder_name)

    async def invite(
        self, folder_name: str, participant_name: str, mode: str = "read-write"
    ) -> dict:
        if mode.lower() not in ("read-write", "read-only"):
            raise ValueError(
                f'Invalid Magic-Folder invite mode, "{mode}"; acceptable '
                'values are: "read-write", "read-only"'
            )
        result = await self._request(
            "POST",
            f"/experimental/magic-folder/{folder_name}/invite",
            body=json.dumps(
                {"participant-name": participant_name, "mode": mode}
            ).encode(),
        )
        return cast(dict, result)

    async def invite_wait(self, folder_name: str, id_: str) -> dict:
        result = await self._request(
            "POST",
            f"/experimental/magic-folder/{folder_name}/invite-wait",
            body=json.dumps({"id": id_}).encode(),
        )
        return cast(dict, result)

    async def invite_cancel(self, folder_name: str, id_: str) -> dict:
        result = await self._request(
            "POST",
            f"/experimental/magic-folder/{folder_name}/invite-cancel",
            body=json.dumps({"id": id_}).encode(),
        )
        return cast(dict, result)

    async def invites(self, folder_name: str) -> list:
        result = await self._request(
            "GET",
            f"/experimental/magic-folder/{folder_name}/invites",
        )
        return cast(list, result)

    async def join(  # pylint: disable=too-many-arguments
        self,
        folder_name: str,
        invite_code: str,
        local_path: Union[str, Path],
        author: str = "user",  # XXX Is this even used for anything?
        poll_interval: int = 60,
        scan_interval: int = 60,
    ) -> dict:
        local_path = Path(local_path).absolute()
        local_path.mkdir(parents=True, exist_ok=True)
        result = await self._request(
            "POST",
            f"/experimental/magic-folder/{folder_name}/join",
            body=json.dumps(
                {
                    "invite-code": invite_code,
                    "local-directory": str(local_path),
                    "author": author,
                    "poll-interval": poll_interval,
                    "scan-interval": scan_interval,
                    "read-only": None,  # XXX Undocumented??
                }
            ).encode(),
        )
        return cast(dict, result)
