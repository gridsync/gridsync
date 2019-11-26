# -*- coding: utf-8 -*-

import json
import os

from gridsync import pkgdir, config_dir, autostart_file_path
from gridsync.crypto import trunchash


def get_filters(core):
    filters = [
        (pkgdir, "PkgDir"),
        (config_dir, "ConfigDir"),
        (autostart_file_path, "AutostartFilePath"),
    ]
    for i, gateway in enumerate(core.gui.main_window.gateways):  # XXX
        gateway_id = i + 1
        filters.append((gateway.name, "GatewayName:{}".format(gateway_id)))
        filters.append((gateway.newscap, "Newscap:{}".format(gateway_id)))
        tahoe_settings = gateway.get_settings(include_rootcap=True)
        filters.append(
            (tahoe_settings.get("rootcap"), "Rootcap:{}".format(gateway_id))
        )
        filters.append(
            (
                tahoe_settings.get("introducer"),
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
        for n, items in enumerate(gateway.magic_folders.items()):
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
                    data.get("admin_dircap"),
                    "Folder:{}:{}:AdminDircap".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    data.get("directory"),
                    "Folder:{}:{}:Directory".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    data.get("member"),
                    "Folder:{}:{}:Member".format(gateway_id, folder_id),
                )
            )
            filters.append(
                (
                    folder_name,
                    "Folder:{}:{}:Name".format(gateway_id, folder_id),
                )
            )
    filters.append((core.executable, "TahoeExecutablePath"))
    filters.append((os.path.expanduser("~"), "HomeDir"))
    return filters


def apply_filters(in_str, filters):
    filtered = in_str
    for s, mask in filters:
        if s and mask:
            filtered = filtered.replace(s, "<Filtered:{}>".format(mask))
    return filtered


def get_mask(string, tag, identifier=None):
    if identifier:
        return "<Filtered:{}>".format(tag + ":" + identifier)
    return "<Filtered:{}>".format(tag + ":" + trunchash(string))


def apply_filter(dictionary, key, tag, identifier=None):
    value = dictionary.get(key)
    if value:
        dictionary[key] = get_mask(value, tag, identifier=identifier)


def _apply_filter_by_action_type(  # noqa: max-complexity=30
    msg, action_type, identifier=None
):
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


def _apply_filter_by_message_type(msg, message_type):  # noqa: max-complexity
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


def filter_tahoe_log_message(message, identifier):
    msg = json.loads(message)

    action_type = msg.get("action_type")
    if action_type:
        _apply_filter_by_action_type(msg, action_type, identifier)

    message_type = msg.get("message_type")
    if message_type:
        _apply_filter_by_message_type(msg, message_type)

    return json.dumps(msg, sort_keys=True)
