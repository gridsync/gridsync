# -*- coding: utf-8 -*-

import json
import os
from collections import OrderedDict
from unittest.mock import Mock

import pytest

from gridsync import autostart_file_path, config_dir, pkgdir
from gridsync.filter import (
    apply_filters,
    filter_tahoe_log_message,
    get_filters,
)


@pytest.fixture
def core():
    c = Mock()
    c.executable = "/tmp/test/tahoe.exe"
    gateway = Mock()
    gateway.name = "TestGrid"
    gateway.newscap = "URI:NEWSCAP"
    storage_settings = OrderedDict()  # Because python3.5
    storage_settings["v0-22222"] = {
        "anonymous-storage-FURL": "pb://333@444.example:1234/5555"
    }
    storage_settings["v0-66666"] = {
        "anonymous-storage-FURL": "pb://777@888.example:1234/9999"
    }
    gateway.get_settings = Mock(
        return_value={
            "rootcap": "URI:000:111",
            "introducer": "pb://aaa@bbb.example:12345/ccc",
            "storage": storage_settings,
        }
    )
    gateway.magic_folders = OrderedDict()  # Because python3.5
    gateway.magic_folders["TestFolder"] = {
        "collective_dircap": "URI:aaa:bbb",
        "upload_dircap": "URI:ccc:ddd",
        "admin_dircap": "URI:eee:fff",
        "directory": "/tmp/test/TestFolder",
        "member": "Alice",
    }
    gateway.magic_folders["CatPics"] = {
        "collective_dircap": "URI:ggg:hhh",
        "upload_dircap": "URI:iii:jjj",
        "admin_dircap": "URI:kkk:lll",
        "directory": "/tmp/test/CatPics",
        "member": "Bob",
    }
    c.gui.main_window.gateways = [gateway]
    return c


@pytest.mark.parametrize(
    "pair",
    [
        (pkgdir, "PkgDir"),
        (config_dir, "ConfigDir"),
        (autostart_file_path, "AutostartFilePath"),
        (os.path.expanduser("~"), "HomeDir"),
    ],
)
def test_get_filters_pair_in_default_filters(core, pair):
    filters = get_filters(core)
    assert pair in filters


@pytest.mark.parametrize(
    "string",
    [
        pkgdir,
        config_dir,
        autostart_file_path,
        "TestGrid",
        "URI:NEWSCAP",
        "URI:000:111",
        "v0-22222",
        "pb://333@444.example:1234/5555",
        "v0-66666",
        "pb://777@888.example:1234/9999",
        "TestFolder",
        "URI:aaa:bbb",
        "URI:ccc:ddd",
        "URI:eee:fff",
        "/tmp/test/TestFolder",
        "Alice",
        "CatPics",
        "URI:ggg:hhh",
        "URI:iii:jjj",
        "URI:kkk:lll",
        "/tmp/test/CatPics",
        "Bob",
        os.path.expanduser("~"),
        "/tmp/test/tahoe.exe",
    ],
)
def test_apply_filters_string_not_in_result(core, string):
    filters = get_filters(core)
    in_str = "Bob gave {} to Alice".format(string)
    result = apply_filters(in_str, filters)
    assert string not in result


@pytest.mark.parametrize(
    "string,filtered",
    [
        (pkgdir, "PkgDir"),
        (config_dir, "ConfigDir"),
        (autostart_file_path, "AutostartFilePath"),
        ("TestGrid", "GatewayName:1"),
        ("URI:NEWSCAP", "Newscap:1"),
        ("URI:000:111", "Rootcap:1"),
        ("v0-22222", "StorageServerName:1:1"),
        ("pb://333@444.example:1234/5555", "StorageServerFurl:1:1"),
        ("v0-66666", "StorageServerName:1:2"),
        ("pb://777@888.example:1234/9999", "StorageServerFurl:1:2"),
        ("URI:aaa:bbb", "Folder:1:1:CollectiveDircap"),
        ("URI:ccc:ddd", "Folder:1:1:UploadDircap"),
        ("URI:eee:fff", "Folder:1:1:AdminDircap"),
        ("/tmp/test/TestFolder", "Folder:1:1:Directory"),
        ("TestFolder", "Folder:1:1:Name"),
        ("Alice", "Folder:1:1:Member"),
        ("URI:ggg:hhh", "Folder:1:2:CollectiveDircap"),
        ("URI:iii:jjj", "Folder:1:2:UploadDircap"),
        ("URI:kkk:lll", "Folder:1:2:AdminDircap"),
        ("/tmp/test/CatPics", "Folder:1:2:Directory"),
        ("CatPics", "Folder:1:2:Name"),
        ("Bob", "Folder:1:2:Member"),
        (os.path.expanduser("~"), "HomeDir"),
        ("/tmp/test/tahoe.exe", "TahoeExecutablePath"),
    ],
)
def test_apply_filters_filtered_string_in_result(core, string, filtered):
    filters = get_filters(core)
    in_str = "Bob gave {} to Alice".format(string)
    result = apply_filters(in_str, filters)
    assert "<Filtered:{}>".format(filtered) in result


@pytest.mark.parametrize(
    "msg,keys",
    [
        (
            {
                "action_type": "dirnode:add-file",
                "action_status": "started",
                "metadata": {
                    "last_downloaded_timestamp": 1554248457.597176,
                    "user_mtime": 1554212870.7714074,
                    "version": 0,
                },
                "name": "lolcat.jpg",
                "overwrite": True,
                "task_level": [4, 3, 5, 6, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248457.597313,
            },
            ["name"],
        ),
        (
            {
                "action_type": "invite-to-magic-folder",
                "action_status": "started",
                "timestamp": 1554305616.315925,
                "client_num": 0,
                "nickname": "Alice\u00f8",
                "task_level": [1],
                "task_uuid": "c0fd93dc-01c3-48e5-a0fa-14028cb83cdc",
            },
            ["nickname"],  # XXX MemberName
        ),
        (
            {
                "action_type": "join-magic-folder",
                "action_status": "started",
                "timestamp": 1554305611.622096,
                "local_dir": "cli/MagicFolder/create-and-then-invite-join/magic",
                "client_num": 0,
                "task_uuid": "41282946-79da-490f-b640-9a0ae349ffb4",
                "task_level": [1],
                "invite_code": "URI:DIR2-RO:3x67kv2fmpz2fji4s775o72yxe:jpi2cfxsc4xjioea735g7fnqdjimkn6scpit4xumkkzk27nfm6pq+URI:DIR2:shiycttqoawwqkonizibpkx5ye:6hv4g33odqojq23g5bq22ej6if6kinytivsmx2gwhuol65fxd2za",
            },
            ["local_dir", "invite_code"],
        ),
        (
            {
                "action_type": "magic-folder-db:update-entry",
                "action_status": "started",
                "last_downloaded_timestamp": 1554248457.008035,
                "last_downloaded_uri": "URI:CHK:452hmzwvthqbsawh6e4ua4plei:6zeihsoigv7xl7ijdmyzfa7wt5rajqhj3ppmaqgxoilt4n5srszq:1:1:201576",
                "last_uploaded_uri": "URI:CHK:452hmzwvthqbsawh6e4ua4plei:6zeihsoigv7xl7ijdmyzfa7wt5rajqhj3ppmaqgxoilt4n5srszq:1:1:201576",
                "pathinfo": {
                    "ctime_ns": 1554212870771407360,
                    "exists": True,
                    "isdir": False,
                    "isfile": True,
                    "islink": False,
                    "mtime_ns": 1554212870771407360,
                    "size": 201576,
                },
                "relpath": "Garfield.jpg",
                "task_level": [4, 3, 4, 7, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248457.573836,
                "version": 0,
            },
            ["last_downloaded_uri", "last_uploaded_uri", "relpath"],
        ),
        (
            {
                "action_type": "magic-folder:add-pending",
                "action_status": "started",
                "relpath": "Grumpy Cat.jpg",
                "task_level": [2, 2, 9, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248455.404073,
            },
            ["relpath"],
        ),
        (
            {
                "action_type": "magic-folder:downloader:get-latest-file",
                "task_uuid": "bb07d7f1-0af0-44ed-9bcb-e60828fcf0a3",
                "task_level": [18, 5, 16, 3, 1],
                "timestamp": 1554305539.486,
                "name": "blam",
                "action_status": "started",
            },
            ["name"],
        ),
        (
            {
                "action_type": "magic-folder:full-scan",
                "action_status": "started",
                "direction": "uploader",
                "nickname": "Demo Grid",
                "task_level": [2, 1],
                "task_uuid": "1f7049fd-1530-4d12-8461-94e42655f1be",
                "timestamp": 1554248626.324124,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:iteration",
                "action_status": "started",
                "direction": "uploader",
                "nickname": "Demo Grid",
                "task_level": [4, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248455.40636,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:notified",
                "action_status": "started",
                "timestamp": 1554305907.525834,
                "nickname": "client-0",
                "task_uuid": "b29934a9-ec4f-44d1-b987-45a8cc0d2ba2",
                "task_level": [7, 4, 2, 1],
                "path": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmpP9HEA2/local_dir/bar",
                "direction": "uploader",
            },
            ["nickname", "path"],
        ),
        (
            {
                "action_type": "magic-folder:process-directory",
                "task_uuid": "bc637a12-9141-41de-b36e-6eccc0a65e86",
                "task_level": [8, 3, 2, 7, 6],
                "timestamp": 1554305529.111,
                "action_status": "succeeded",
                "created_directory": "subdir",
            },
            ["created_directory"],
        ),
        (
            {
                "action_type": "magic-folder:process-item",
                "action_status": "started",
                "item": {"relpath": "Garfield.jpg", "size": 201576},
                "task_level": [13, 3, 2, 1],
                "task_uuid": "d3a0e3db-3cd6-49c5-9847-7c742b6eec56",
                "timestamp": 1554250168.097768,
            },
            ["item"],  # XXX dict with relpath
        ),
        (
            {
                "action_type": "magic-folder:processing-loop",
                "action_status": "started",
                "direction": "uploader",
                "nickname": "Demo Grid",
                "task_level": [3, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248455.406146,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:remove-from-pending",
                "action_status": "started",
                "pending": [
                    "Cheshire Cat.jpeg",
                    "Kitler.png",
                    "Colonel Meow.jpg",
                    "Waffles.jpg",
                    "Grumpy Cat.jpg",
                    "lolcat.jpg",
                ],
                "relpath": "lolcat.jpg",
                "task_level": [4, 3, 5, 3, 1],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248457.596115,
            },
            ["pending", "relpath"],  # XXX list of paths
        ),
        (
            {
                "action_type": "magic-folder:rename-conflicted",
                "abspath_u": "/Users/vagrant/tahoe-lafs/_trial_temp/cli/MagicFolder/write-downloaded-file/foobar",
                "action_status": "started",
                "timestamp": 1554305923.406739,
                "replacement_path_u": "/Users/vagrant/tahoe-lafs/_trial_temp/cli/MagicFolder/write-downloaded-file/foobar.tmp",
                "task_level": [7, 2, 1],
                "task_uuid": "9e88518e-d2f4-4459-babc-e45e8a24034d",
            },
            ["abspath_u", "replacement_path_u"],
        ),
        (
            {
                "action_type": "magic-folder:rename-conflicted",
                "task_level": [7, 2, 2],
                "timestamp": 1554305923.408401,
                "result": "/Users/vagrant/tahoe-lafs/_trial_temp/cli/MagicFolder/write-downloaded-file/foobar.conflict",
                "action_type": "magic-folder:rename-conflicted",
                "action_status": "succeeded",
                "task_uuid": "9e88518e-d2f4-4459-babc-e45e8a24034d",
            },
            ["result"],
        ),
        (
            {
                "action_type": "magic-folder:rename-deleted",
                "abspath_u": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmp1cdGlh/Bob-magic/file1",
                "task_level": [18, 5, 17, 4, 3, 3, 1],
                "timestamp": 1554305926.082758,
                "action_status": "started",
                "task_uuid": "14100717-85cd-41bc-bb1c-eadc418e760b",
            },
            ["abspath_u"],
        ),
        (
            {
                "action_type": "magic-folder:rename-deleted",
                "task_level": [18, 5, 17, 4, 3, 3, 2],
                "timestamp": 1554305926.083676,
                "result": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmp1cdGlh/Bob-magic/file1",
                "action_type": "magic-folder:rename-deleted",
                "action_status": "succeeded",
                "task_uuid": "14100717-85cd-41bc-bb1c-eadc418e760b",
            },
            ["result"],
        ),
        (
            {
                "action_type": "magic-folder:scan-remote-dmd",
                "action_status": "started",
                "nickname": "admin",
                "task_level": [3, 2, 1],
                "task_uuid": "5816398c-a658-4b59-8526-f8052f63e114",
                "timestamp": 1554248455.52203,
            },
            ["nickname"],  # XXX MemberName
        ),
        (
            {
                "action_type": "magic-folder:start-downloading",
                "action_status": "started",
                "direction": "downloader",
                "nickname": "Demo Grid",
                "task_level": [1],
                "task_uuid": "5816398c-a658-4b59-8526-f8052f63e114",
                "timestamp": 1554248455.417441,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:start-monitoring",
                "action_status": "started",
                "direction": "uploader",
                "nickname": "Demo Grid",
                "task_level": [1],
                "task_uuid": "e03e0c60-870f-43e3-ae87-5808728ad7ee",
                "timestamp": 1554248454.973468,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:start-uploading",
                "action_status": "started",
                "direction": "uploader",
                "nickname": "Demo Grid",
                "task_level": [1],
                "task_uuid": "1f7049fd-1530-4d12-8461-94e42655f1be",
                "timestamp": 1554248626.323862,
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:stop",
                "task_uuid": "18bceae8-4f93-4f96-8ccf-cc51986355c6",
                "task_level": [25, 1],
                "timestamp": 1554305541.345,
                "nickname": "magic-folder-default",
                "action_status": "started",
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:stop-monitoring",
                "action_status": "started",
                "task_level": [18, 5, 12, 4, 7, 2, 1],
                "timestamp": 1554305542.267,
                "nickname": "client-0",
                "task_uuid": "d7a30d64-992b-48ca-a0e9-84cb0d55ea37",
                "direction": "uploader",
            },
            ["nickname"],
        ),
        (
            {
                "action_type": "magic-folder:write-downloaded-file",
                "mtime": 1554305970.0,
                "is_conflict": False,
                "timestamp": 1554305970.864801,
                "abspath": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmp4Rwmkc/Bob-magic/file2",
                "task_level": [20, 5, 41, 4, 3, 3, 2, 1],
                "size": 9,
                "task_uuid": "4ac59194-cbbf-43d4-8c36-c940541b608e",
                "action_status": "started",
                "now": 1554305970.864769,
            },
            ["abspath"],
        ),
        (
            {
                "action_type": "notify-when-pending",
                "task_level": [9, 3, 1],
                "timestamp": 1554305908.530923,
                "filename": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmpC02XVl/local_dir/subdir/some-file",
                "action_status": "started",
                "task_uuid": "19b59820-a424-4773-8fd5-e6a5f2655339",
            },
            ["filename"],
        ),
        (
            {
                "action_type": "watchdog:inotify:any-event",
                "event": "FileCreatedEvent",
                "action_status": "started",
                "timestamp": 1554305884.723024,
                "path": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmp_mEbEu/foo.bar",
                "task_level": [1],
                "task_uuid": "e03ccbec-f120-49a3-9264-1ae63fdb3c5e",
            },
            ["path"],
        ),
    ],
)
def test__apply_filter_by_action_type(msg, keys):
    for key in keys:
        original_value = str(msg.get(key))
        filtered_msg = filter_tahoe_log_message(json.dumps(msg), "1")
        assert original_value not in filtered_msg


@pytest.mark.parametrize(
    "msg,keys",
    [
        (
            {
                "message_type": "fni",
                "task_uuid": "564c8258-e36c-4455-95f0-a8c6b1abb481",
                "info": "Event('FILE_ACTION_ADDED', u'blam.tmp')",
                "task_level": [1],
                "timestamp": 1554305542.236,
            },
            ["info"],
        ),
        (
            {
                "message_type": "magic-folder:add-to-download-queue",
                "timestamp": 1554308128.248248,
                "task_level": [79, 2, 2, 2, 6],
                "task_uuid": "1dbadb17-3260-46d4-9a10-6177a5309060",
                "relpath": "/tmp/magic_folder_test",
            },
            ["relpath"],
        ),
        (
            {
                "message_type": "magic-folder:all-files",
                "task_uuid": "3082ca20-b897-45d6-9f65-a2ed4574f2d2",
                "task_level": [14, 2, 3, 2],
                "timestamp": 1554305532.329,
                "files": ["what1"],
            },
            ["files"],
        ),
        (
            {
                "message_type": "magic-folder:downloader:get-latest-file:collective-scan",
                "task_uuid": "a331e6e8-8e07-4393-9e49-fa2e1af46fa4",
                "task_level": [18, 5, 10, 2, 2],
                "timestamp": 1554305538.049,
                "dmds": ["Alice\u00f8", "Bob\u00f8"],
            },
            ["dmds"],
        ),
        (
            {
                "message_type": "magic-folder:item:status-change",
                "relpath": "foo",
                "task_level": [6, 4, 2, 2, 2, 2],
                "timestamp": 1554305907.522427,
                "status": "queued",
                "task_uuid": "b29934a9-ec4f-44d1-b987-45a8cc0d2ba2",
            },
            ["relpath"],
        ),
        (
            {
                "message_type": "magic-folder:maybe-upload",
                "relpath": "subdir/some-file",
                "task_level": [10, 3, 2, 5],
                "timestamp": 1554305908.534811,
                "task_uuid": "19b59820-a424-4773-8fd5-e6a5f2655339",
            },
            ["relpath"],
        ),
        (
            {
                "message_type": "magic-folder:notified-object-disappeared",
                "timestamp": 1554305910.549119,
                "task_level": [11, 3, 2, 5],
                "path": "/Users/vagrant/tahoe-lafs/_trial_temp/immutable/Test/code/clients/2g45r67f/tmp/tmpY7_3G4/local_dir/foo",
                "task_uuid": "b5d0c0ee-c4d1-4765-b1ed-e7ff5f556dc5",
            },
            ["path"],
        ),
        (
            {
                "message_type": "magic-folder:remote-dmd-entry",
                "pathentry": {
                    "ctime_ns": 1554212870771407360,
                    "last_downloaded_timestamp": 1554248457.008035,
                    "last_downloaded_uri": "URI:CHK:452hmzwvthqbsawh6e4ua4plei:6zeihsoigv7xl7ijdmyzfa7wt5rajqhj3ppmaqgxoilt4n5srszq:1:1:201576",
                    "last_uploaded_uri": "URI:CHK:452hmzwvthqbsawh6e4ua4plei:6zeihsoigv7xl7ijdmyzfa7wt5rajqhj3ppmaqgxoilt4n5srszq:1:1:201576",
                    "mtime_ns": 1554212870771407360,
                    "size": 201576,
                    "version": 0,
                },
                "relpath": "Garfield.jpg",
                "remote_uri": "URI:CHK:452hmzwvthqbsawh6e4ua4plei:6zeihsoigv7xl7ijdmyzfa7wt5rajqhj3ppmaqgxoilt4n5srszq:1:1:201576",
                "remote_version": 0,
                "task_level": [3, 2, 2],
                "task_uuid": "cab6c818-50d8-4759-a53a-bd0bb64a2062",
                "timestamp": 1554248626.503385,
            },
            ["pathentry", "relpath", "remote_uri"],
        ),
        (
            {
                "message_type": "magic-folder:scan-batch",
                "batch": ["/tmp/magic_folder_test"],
                "task_level": [50, 2, 2, 3, 3],
                "timestamp": 1554305971.962848,
                "task_uuid": "4ac59194-cbbf-43d4-8c36-c940541b608e",
            },
            ["batch"],
        ),
        (
            {
                "message_type": "magic-folder:item:status-change",
                "relpath": "Grumpy Cat.jpg",
                "status": "queued",
                "task_level": [2, 2, 9, 2],
                "task_uuid": "c7a1ec7e-93c1-4549-b916-adc28cda73a1",
                "timestamp": 1554248455.404471,
            },
            ["relpath"],
        ),
        (
            {
                "message_type": "processing",
                "task_uuid": "19595202-3d20-441f-946e-d409709130d4",
                "info": "Event('FILE_ACTION_MODIFIED', u'blam.tmp')",
                "task_level": [1],
                "timestamp": 1554305535.829,
            },
            ["info"],
        ),
    ],
)
def test__apply_filter_by_message_type(msg, keys):
    for key in keys:
        original_value = str(msg.get(key))
        filtered_msg = filter_tahoe_log_message(json.dumps(msg), "1")
        assert original_value not in filtered_msg
