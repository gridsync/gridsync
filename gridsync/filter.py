# -*- coding: utf-8 -*-

import json
import os

from gridsync import pkgdir, config_dir, autostart_file_path
from gridsync.crypto import trunchash


def get_filters(core):
    filters = [
        (pkgdir, 'PkgDir'),
        (config_dir, 'ConfigDir'),
        (autostart_file_path, 'AutostartFilePath'),
    ]
    for i, gateway in enumerate(core.gui.main_window.gateways):  # XXX
        gateway_id = i + 1
        filters.append((gateway.name, 'GatewayName:{}'.format(gateway_id)))
        tahoe_settings = gateway.get_settings(include_rootcap=True)
        filters.append((
            tahoe_settings.get('rootcap'), 'Rootcap:{}'.format(gateway_id)
        ))
        filters.append((
            tahoe_settings.get('introducer'),
            'IntroducerFurl:{}'.format(gateway_id)
        ))
        storage_settings = tahoe_settings.get('storage')
        if storage_settings:
            for n, items in enumerate(storage_settings.items()):
                server_id = n + 1
                server_name, data = items
                filters.append((
                    data.get('anonymous-storage-FURL'),
                    'StorageServerFurl:{}:{}'.format(gateway_id, server_id),
                ))
                filters.append((
                    server_name,
                    'StorageServerName:{}:{}'.format(gateway_id, server_id),
                ))
        for n, items in enumerate(gateway.magic_folders.items()):
            folder_id = n + 1
            folder_name, data = items
            filters.append((
                data.get('collective_dircap'),
                'Folder:{}:{}:CollectiveDircap'.format(gateway_id, folder_id),
            ))
            filters.append((
                data.get('upload_dircap'),
                'Folder:{}:{}:UploadDircap'.format(gateway_id, folder_id),
            ))
            filters.append((
                data.get('admin_dircap'),
                'Folder:{}:{}:AdminDircap'.format(gateway_id, folder_id),
            ))
            filters.append((
                data.get('directory'),
                'Folder:{}:{}:Directory'.format(gateway_id, folder_id),
            ))
            filters.append((
                data.get('member'),
                'Folder:{}:{}:Member'.format(gateway_id, folder_id),
            ))
            filters.append((
                folder_name, 'Folder:{}:{}:Name'.format(gateway_id, folder_id),
            ))
    filters.append((os.path.expanduser('~'), 'HomeDir'))
    filters.append((core.executable, 'TahoeExecutablePath'))
    return filters


def apply_filters(in_str, filters):
    filtered = in_str
    for s, mask in filters:
        if s and mask:
            filtered = filtered.replace(s, '<Filtered:{}>'.format(mask))
    return filtered


def get_mask(string, tag, identifier=None):
    if identifier:
        return '<Filtered:{}>'.format(tag + ':' + identifier)
    return '<Filtered:{}>'.format(tag + ':' + trunchash(string))


def apply_filter(dictionary, key, tag, identifier=None):
    value = dictionary.get(key)
    if value:
        dictionary[key] = get_mask(value, tag, identifier=identifier)


def filter_tahoe_log_message(message, identifier):
    msg = json.loads(message)

    action_type = msg.get('action_type')
    if action_type:
        # In the "magic-folder:scan-remote-dmd" action type, "nickname"
        # refers to the name of the subdirectory in the magic-folder DMD
        # for which only one given "member" typically has write access. In
        # "magic-folder:start-uploading", "magic-folder:start-downloading",
        # "magic-folder:start-monitoring", "magic-folder:processing-loop",
        # "magic-folder:iteration", and "magic-folder:full-scan", it refers
        # instead to the name of the local client node as assigned via the
        # "nickname" field in tahoe.cfg.
        if action_type == 'magic-folder:scan-remote-dmd':
            apply_filter(msg, 'nickname', 'MemberName')
        else:
            apply_filter(msg, 'nickname', 'GatewayName', identifier)

    # TODO: Filter others by 'action_type'/'message_type' too?

    apply_filter(msg, 'relpath', 'Path')
    apply_filter(msg, 'remote_uri', 'Capability')

    pending = msg.get('pending')
    if pending:
        new = []
        for path in pending:
            new.append(get_mask(path, 'Path'))
        msg['pending'] = new

    files = msg.get('files')
    if files:
        new = []
        for path in files:
            new.append(get_mask(path, 'Path'))
        msg['files'] = new

    pathentry = msg.get('pathentry')
    if pathentry:
        last_downloaded_uri = pathentry.get('last_downloaded_uri')
        if last_downloaded_uri:
            pathentry['last_downloaded_uri'] = get_mask(
                last_downloaded_uri, 'Capability')
        last_uploaded_uri = pathentry.get('last_uploaded_uri')
        if last_uploaded_uri:
            pathentry['last_uploaded_uri'] = get_mask(
                last_uploaded_uri, 'Capability')

    return json.dumps(msg, sort_keys=True)
