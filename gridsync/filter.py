# -*- coding: utf-8 -*-

import os

from gridsync import pkgdir, config_dir, autostart_file_path


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
