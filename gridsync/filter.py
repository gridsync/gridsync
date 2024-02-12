# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Optional

from gridsync import autostart_file_path, config_dir, pkgdir
from gridsync.crypto import trunchash

if TYPE_CHECKING:
    from gridsync.core import Core


def is_eliot_log_message(s: str) -> bool:
    try:
        data = json.loads(s)
    except json.decoder.JSONDecodeError:
        return False
    if isinstance(data, dict) and "timestamp" in data and "task_uuid" in data:
        return True
    return False


def get_filters(core: Core) -> list:
    filters = [
        (pkgdir, "PkgDir"),
        (config_dir, "ConfigDir"),
        (autostart_file_path, "AutostartFilePath"),
    ]
    for i, gateway in enumerate(core.gui.main_window.gateways):  # XXX
        gateway_id = i + 1
        filters.append((gateway.name, "GatewayName:{}".format(gateway_id)))
        filters.append((gateway.newscap, "Newscap:{}".format(gateway_id)))
        filters.append((gateway.executable, "TahoeExecutablePath"))
        tahoe_settings = gateway.get_settings(include_secrets=True)
        filters.append(
            (
                tahoe_settings.get("rootcap", ""),
                "Rootcap:{}".format(gateway_id),
            )
        )
        filters.append(
            (
                tahoe_settings.get("introducer", ""),
                "IntroducerFurl:{}".format(gateway_id),
            )
        )
        storage_settings = tahoe_settings.get("storage")
        if storage_settings:
            for n, items in enumerate(storage_settings.items()):
                server_id = n + 1
                server_name, data = items
                filters.append(
                    (
                        data.get("anonymous-storage-FURL"),
                        "StorageServerFurl:{}:{}".format(
                            gateway_id, server_id
                        ),
                    )
                )
                filters.append(
                    (
                        server_name,
                        "StorageServerName:{}:{}".format(
                            gateway_id, server_id
                        ),
                    )
                )
        for n, items in enumerate(gateway.magic_folder.magic_folders.items()):
            folder_id = n + 1
            folder_name, data = items
            filters.append(
                (
                    data.get("collective_dircap"),
                    "Folder:{}:{}:CollectiveDircap".format(
                        gateway_id, folder_id
                    ),
                )
            )
            filters.append(
                (
                    data.get("upload_dircap"),
                    "Folder:{}:{}:UploadDircap".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    data.get("magic_path"),
                    "Folder:{}:{}:MagicPath".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    folder_name,
                    "Folder:{}:{}:Name".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    data.get("author", {}).get("name"),
                    "Folder:{}:{}:AuthorName".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    data.get("author", {}).get("signing_key"),
                    "Folder:{}:{}:AuthorSigningKey".format(
                        gateway_id, folder_id
                    ),
                )
            )
            filters.append(
                (
                    data.get("author", {}).get("verify_key"),
                    "Folder:{}:{}:AuthorVerifyKey".format(
                        gateway_id, folder_id
                    ),
                )
            )
    filters.append((os.path.expanduser("~"), "HomeDir"))
    return filters


def apply_filters(in_str: str, filters: list) -> str:
    filtered = in_str
    for s, mask in filters:
        if s and mask:
            filtered = filtered.replace(s, "<Filtered:{}>".format(mask))
    return filtered


def get_mask(string: str, tag: str, identifier: Optional[str] = None) -> str:
    if identifier:
        return "<Filtered:{}>".format(tag + ":" + identifier)
    return "<Filtered:{}>".format(tag + ":" + trunchash(string))


def apply_filter(
    dictionary: dict, key: str, tag: str, identifier: Optional[str] = None
) -> None:
    value = dictionary.get(key)
    if value:
        dictionary[key] = get_mask(value, tag, identifier=identifier)


def _apply_filter_by_action_type(  # noqa: C901 [max-complexity]
    msg: dict, action_type: str, identifier: Optional[str] = None
) -> dict:
    if action_type == "dirnode:add-file":
        apply_filter(msg, "name", "Path")

    elif action_type == "invite-to-magic-folder":
        apply_filter(msg, "nickname", "MemberName")

    elif action_type == "join-magic-folder":
        apply_filter(msg, "local_dir", "Path")
        apply_filter(msg, "invite_code", "InviteCode")

    elif action_type == "magic-folder-db:update-entry":
        apply_filter(msg, "last_downloaded_uri", "Capability")
        apply_filter(msg, "last_uploaded_uri", "Capability")
        apply_filter(msg, "relpath", "Path")

    elif action_type == "magic-folder:add-pending":
        apply_filter(msg, "relpath", "Path")

    elif action_type == "magic-folder:downloader:get-latest-file":
        apply_filter(msg, "name", "Path")

    elif action_type == "magic-folder:full-scan":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:iteration":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:notified":
        apply_filter(msg, "nickname", "GatewayName", identifier)
        apply_filter(msg, "path", "Path")

    elif action_type == "magic-folder:process-directory":
        apply_filter(msg, "created_directory", "Path")

    elif action_type == "magic-folder:process-item":
        item = msg.get("item")
        if item:
            relpath = item.get("relpath")
            if relpath:
                msg["item"]["relpath"] = get_mask(relpath, "Path")

    elif action_type == "magic-folder:processing-loop":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:remove-from-pending":
        apply_filter(msg, "relpath", "Path")
        pending = msg.get("pending")
        if pending:
            new = []
            for path in pending:
                new.append(get_mask(path, "Path"))
            msg["pending"] = new

    elif action_type == "magic-folder:rename-conflicted":
        apply_filter(msg, "abspath_u", "Path")
        apply_filter(msg, "replacement_path_u", "Path")
        apply_filter(msg, "result", "Path")

    elif action_type == "magic-folder:rename-deleted":
        apply_filter(msg, "abspath_u", "Path")
        apply_filter(msg, "result", "Path")

    elif action_type == "magic-folder:scan-remote-dmd":
        apply_filter(msg, "nickname", "MemberName")

    elif action_type == "magic-folder:start-downloading":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:start-monitoring":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:start-uploading":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:stop":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:stop-monitoring":
        apply_filter(msg, "nickname", "GatewayName", identifier)

    elif action_type == "magic-folder:write-downloaded-file":
        apply_filter(msg, "abspath", "Path")

    elif action_type == "notify-when-pending":
        apply_filter(msg, "filename", "Path")

    elif action_type == "watchdog:inotify:any-event":
        apply_filter(msg, "path", "Path")

    return msg


def _apply_filter_by_message_type(  # noqa: C901 [max-complexity]
    msg: dict, message_type: str
) -> dict:
    if message_type == "fni":
        apply_filter(msg, "info", "Event")

    elif message_type == "magic-folder:add-to-download-queue":
        apply_filter(msg, "relpath", "Path")

    elif message_type == "magic-folder:all-files":
        files = msg.get("files")
        if files:
            new = []
            for path in files:
                new.append(get_mask(path, "Path"))
            msg["files"] = new

    elif message_type == (
        "magic-folder:downloader:get-latest-file:collective-scan"
    ):
        dmds = msg.get("dmds")
        if dmds:
            new = []
            for dmd in dmds:
                new.append(get_mask(dmd, "MemberName"))
            msg["dmds"] = new

    elif message_type == "magic-folder:item:status-change":
        apply_filter(msg, "relpath", "Path")

    elif message_type == "magic-folder:maybe-upload":
        apply_filter(msg, "relpath", "Path")

    elif message_type == "magic-folder:notified-object-disappeared":
        apply_filter(msg, "path", "Path")

    elif message_type == "magic-folder:remote-dmd-entry":
        apply_filter(msg, "relpath", "Path")
        apply_filter(msg, "remote_uri", "Capability")
        pathentry = msg.get("pathentry")
        if pathentry:
            last_downloaded_uri = pathentry.get("last_downloaded_uri")
            if last_downloaded_uri:
                pathentry["last_downloaded_uri"] = get_mask(
                    last_downloaded_uri, "Capability"
                )
            last_uploaded_uri = pathentry.get("last_uploaded_uri")
            if last_uploaded_uri:
                pathentry["last_uploaded_uri"] = get_mask(
                    last_uploaded_uri, "Capability"
                )

    elif message_type == "magic-folder:scan-batch":
        batch = msg.get("batch")
        if batch:
            new = []
            for path in batch:
                new.append(get_mask(path, "Path"))
            msg["batch"] = new

    elif message_type == "processing":
        apply_filter(msg, "info", "Event")

    return msg


def filter_eliot_log_message(
    message: str, identifier: Optional[str] = None
) -> str:
    msg = json.loads(message)

    action_type = msg.get("action_type")
    if action_type:
        _apply_filter_by_action_type(msg, action_type, identifier)

    message_type = msg.get("message_type")
    if message_type:
        _apply_filter_by_message_type(msg, message_type)

    return json.dumps(msg, sort_keys=True)


def filter_eliot_logs(
    messages: list[str], identifier: Optional[str] = None
) -> list[str]:
    filtered = []
    for message in messages:
        if message:
            filtered.append(filter_eliot_log_message(message, identifier))
    return filtered


def join_eliot_logs(messages: list[str]) -> str:
    reordered = []
    for message in messages:
        if message:
            reordered.append(json.dumps(json.loads(message), sort_keys=True))
    return "\n".join(reordered)


def apply_eliot_filters(content: str, identifier: Optional[str] = None) -> str:
    messages = content.split("\n")
    return join_eliot_logs(filter_eliot_logs(messages, identifier))
