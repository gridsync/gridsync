# -*- coding: utf-8 -*-

import json
import os
from unittest.mock import Mock

import pytest

from gridsync.news import NewscapChecker
from gridsync.tahoe import TahoeWebError


@pytest.fixture()
def newscap_checker(tahoe):
    return NewscapChecker(tahoe)


def test_newscap_checker_init_override_check_delay_values(tahoe, monkeypatch):
    gateway_name = tahoe.name
    global_settings = {
        "news:{}".format(gateway_name): {
            "check_delay_min": "12",
            "check_delay_max": "34",
        }
    }
    monkeypatch.setattr("gridsync.news.settings", global_settings)
    nc = NewscapChecker(tahoe)
    assert (nc.check_delay_min, nc.check_delay_max) == (12, 34)


def test_newscap_checker_init_delay_max_not_less_than_min(tahoe, monkeypatch):
    gateway_name = tahoe.name
    global_settings = {
        "news:{}".format(gateway_name): {
            "check_delay_min": "78",
            "check_delay_max": "56",
        }
    }
    monkeypatch.setattr("gridsync.news.settings", global_settings)
    nc = NewscapChecker(tahoe)
    assert (nc.check_delay_min, nc.check_delay_max) == (78, 78)


def test_newscap_checker__download_messages(newscap_checker, monkeypatch):
    fake_download = Mock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.download", fake_download)
    downloads = [("dest01", "filecap01"), ("dest02", "filecap02")]
    newscap_checker._download_messages(downloads)
    assert fake_download.call_count == 2


def test_newscap_checker__download_messages_warn(newscap_checker, monkeypatch):
    fake_download = Mock(side_effect=TahoeWebError)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.download", fake_download)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    downloads = [("dest01", "filecap01"), ("dest02", "filecap02")]
    newscap_checker._download_messages(downloads)
    assert fake_logging_warning.call_count == 2


def test_newscap_checker__download_emit_message_received_signal_newest_file(
    newscap_checker, monkeypatch, qtbot
):
    fake_download = Mock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.download", fake_download)
    newscap_messages_dir = os.path.join(
        newscap_checker.gateway.nodedir, "private", "newscap_messages"
    )
    os.makedirs(newscap_messages_dir)
    dest01_path = os.path.join(newscap_messages_dir, "dest01")
    with open(dest01_path, "w") as f:
        f.write("dest01 contents")
    dest02_path = os.path.join(newscap_messages_dir, "dest02")
    with open(dest02_path, "w") as f:
        f.write("dest02 contents")
    downloads = [(dest01_path, "filecap01"), (dest02_path, "filecap02")]
    with qtbot.wait_signal(newscap_checker.message_received) as blocker:
        newscap_checker._download_messages(downloads)
    assert blocker.args == [newscap_checker.gateway, "dest02 contents"]


def test_newscap_checker__check_v1_return_early_no_content(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: None)
    fake__download_messages = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._download_messages",
        fake__download_messages,
    )
    newscap_checker._check_v1()
    assert fake__download_messages.call_count == 0


def test_newscap_checker__check_v1_return_early_warn_index_error(
    newscap_checker, monkeypatch
):
    content = ["test"]
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker._check_v1()
    assert fake_logging_warning.call_args[0][1] == "IndexError"


def test_newscap_checker__check_v1_return_early_warn_key_error(
    newscap_checker, monkeypatch
):
    content = ["test", {"test": "testing"}]
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker._check_v1()
    assert fake_logging_warning.call_args[0][1] == "KeyError"


v1_json = """
[
 "dirnode",
 {
  "mutable": true,
  "verify_uri": "URI:DIR2-Verifier:n7c4sxon4zlryged56f46vq4je:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
  "ro_uri": "URI:DIR2-RO:cnqrbhvh3slxtp3cuaka2qdwna:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
  "children": {
   "TESTDIR": [
     "dirnode",
     {
      "mutable": true,
      "verify_uri": "URI:DIR2-Verifier:f2qunbegglatcgozz3w6ccf3ri:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjklmcsq",
      "ro_uri": "URI:DIR2-RO:me7spfy6qzsq67nwom3zaw3ceu:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjklmcsq",
      "metadata": {
       "tahoe": {
        "linkmotime": 1555020005.536544,
        "linkcrtime": 1555020005.536544
       }
      }
     }
    ],
    "2019-04-16T16:26:53-04:00.txt": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:mi7mfbyv4xawf7miwd4t5dwnbf:lteimsasc5w4ssl7r6f7talacblco4sahujl53l62454e5pova5a:1:1:95",
     "ro_uri": "URI:CHK:6tv4nfbaox27ni5aonexetqvij:lteimsasc5w4ssl7r6f7talacblco4sahujl53l62454e5pova5a:1:1:95",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555446415.491253,
       "linkcrtime": 1555446415.491253
      }
     },
     "size": 95
    }
   ],
   "2019-04-16T16:26:20-04:00.txt": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:g23pmtrycqzlb2o324zzdihtsm:4xdbm432twerlqodefmei5bf4bz5ehezhnh2grmc7alvg7srf74q:1:1:92",
     "ro_uri": "URI:CHK:4hm7mrgw2qav72jeq5j7jjcwve:4xdbm432twerlqodefmei5bf4bz5ehezhnh2grmc7alvg7srf74q:1:1:92",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555446382.523451,
       "linkcrtime": 1555446382.523451
      }
     },
     "size": 92
    }
   ]
  }
 }
]
"""


def test_newscap_checker__check_v1_make_messages_dirpath(
    newscap_checker, monkeypatch
):
    content = json.loads(v1_json)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    fake__download_messages = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._download_messages",
        fake__download_messages,
    )
    newscap_checker._check_v1()
    messages_dirpath = os.path.join(
        newscap_checker.gateway.nodedir, "private", "newscap_messages"
    )
    assert os.path.exists(messages_dirpath)


def test_newscap_checker__check_v1_append_downloads_win32_replace_colon(
    newscap_checker, monkeypatch
):
    content = json.loads(v1_json)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    fake__download_messages = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._download_messages",
        fake__download_messages,
    )
    monkeypatch.setattr("sys.platform", "win32")
    newscap_checker._check_v1()
    messages_dirpath = os.path.join(
        newscap_checker.gateway.nodedir, "private", "newscap_messages"
    )
    assert sorted(fake__download_messages.call_args[0][0]) == [
        (
            os.path.join(messages_dirpath, "2019-04-16T16_26_20-04_00.txt"),
            "URI:CHK:4hm7mrgw2qav72jeq5j7jjcwve:4xdbm432twerlqodefmei5bf4bz5ehezhnh2grmc7alvg7srf74q:1:1:92",
        ),
        (
            os.path.join(messages_dirpath, "2019-04-16T16_26_53-04_00.txt"),
            "URI:CHK:6tv4nfbaox27ni5aonexetqvij:lteimsasc5w4ssl7r6f7talacblco4sahujl53l62454e5pova5a:1:1:95",
        ),
    ]


def test_newscap_checker__do_check_return_early_no_newscap(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    fake_await_ready = Mock()
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", fake_await_ready)
    newscap_checker._do_check()
    assert fake_await_ready.call_count == 0


def test_newscap_checker__do_check_return_early_no_content(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: None)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert not os.path.exists(newscap_checker._last_checked_path)


def test_newscap_checker__do_check_return_early_warn_index_error(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = ["test"]
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert fake_logging_warning.call_args[0][1] == "IndexError"


def test_newscap_checker__do_check_return_early_warn_key_error(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = ["test", {"test": "testing"}]
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert fake_logging_warning.call_args[0][1] == "KeyError"


root_json_with_v2 = """
[
 "dirnode",
 {
  "mutable": true,
  "verify_uri": "URI:DIR2-Verifier:mi3ac77qzzoclhakj3772cufxe:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "ro_uri": "URI:DIR2-RO:zjxovy5umhhbbzwn6gweo2jtg5:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "children": {
   "TESTDIR": [
    "dirnode",
    {
     "mutable": true,
     "verify_uri": "URI:DIR2-Verifier:f3qunbegglatcgozz3w6ccf3ri:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjilmcsq",
     "ro_uri": "URI:DIR2-RO:me6spfy6qzsq67nwom3zaw3ceu:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjilmcsq",
     "metadata": {
      "tahoe": {
       "linkmotime": 1555020005.536544,
       "linkcrtime": 1555020005.536544
      }
     }
    }
   ],
   "v1": [
    "dirnode",
    {
     "mutable": true,
     "verify_uri": "URI:DIR2-Verifier:n7c4sxon4zlryged56f46vq4je:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
     "ro_uri": "URI:DIR2-RO:cnqrbhvh3slxtp3cuaka2qdwna:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
     "metadata": {
      "tahoe": {
       "linkmotime": 1555026307.973014,
       "linkcrtime": 1555026307.973014
      }
     }
    }
   ],
   "v2": [
    "dirnode",
    {
     "mutable": true,
     "verify_uri": "URI:DIR2-Verifier:dgehdhwkwvjhfsva7beabmqyim:pju5tewhkeyav2myhxczypcs6nkcg324npquz7ajfobb52k5llic",
     "ro_uri": "URI:DIR2-RO:r2oml37ehxf6n7kqc5xsbk2hdq:pju5tewhkeyav2myhxczypcs6nkcg324npquz7ajfobb52k5llic",
     "metadata": {
      "tahoe": {
       "linkmotime": 1555030372.132256,
       "linkcrtime": 1555030372.132256
      }
     }
    }
   ],
   "test.txt": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:i3epgjv2cjppjcoco2v7qlusmw:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "ro_uri": "URI:CHK:xnw2fjq7zmsw74bmwu7kdsffpn:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555017261.25157,
       "linkcrtime": 1555017261.25157
      }
     },
     "size": 90
    }
   ]
  }
 }
]
"""


def test_newscap_checker__do_check_emit_upgrade_required_signal(
    newscap_checker, monkeypatch, qtbot
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = json.loads(root_json_with_v2)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake__check_v1 = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._check_v1", fake__check_v1
    )
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    with qtbot.wait_signal(newscap_checker.upgrade_required) as blocker:
        newscap_checker._do_check()
    assert blocker.args == [newscap_checker.gateway]


root_json_without_v2 = """
[
 "dirnode",
 {
  "mutable": true,
  "verify_uri": "URI:DIR2-Verifier:mi3ac77qzzoclhakj3772cufxe:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "ro_uri": "URI:DIR2-RO:zjxovy5umhhbbzwn6gweo2jtg5:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "children": {
   "TESTDIR": [
    "dirnode",
    {
     "mutable": true,
     "verify_uri": "URI:DIR2-Verifier:f3qunbegglatcgozz3w6ccf3ri:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjilmcsq",
     "ro_uri": "URI:DIR2-RO:me6spfy6qzsq67nwom3zaw3ceu:jnjqqsc2cxoajb4xz4qetdxhl6koynynhk35fvv5prq4rjilmcsq",
     "metadata": {
      "tahoe": {
       "linkmotime": 1555020005.536544,
       "linkcrtime": 1555020005.536544
      }
     }
    }
   ],
   "v1": [
    "dirnode",
    {
     "mutable": true,
     "verify_uri": "URI:DIR2-Verifier:n7c4sxon4zlryged56f46vq4je:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
     "ro_uri": "URI:DIR2-RO:cnqrbhvh3slxtp3cuaka2qdwna:myrodlgvr5fynrls4kz5vsnv5qddmgi2yk75vfv5rv6e4t65vjdb",
     "metadata": {
      "tahoe": {
       "linkmotime": 1555026307.973014,
       "linkcrtime": 1555026307.973014
      }
     }
    }
   ],
   "test.txt": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:i3epgjv2cjppjcoco2v7qlusmw:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "ro_uri": "URI:CHK:xnw2fjq7zmsw74bmwu7kdsffpn:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555017261.25157,
       "linkcrtime": 1555017261.25157
      }
     },
     "size": 90
    }
   ]
  }
 }
]
"""


def test_newscap_checker__do_check_call__check_v1(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = json.loads(root_json_without_v2)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake__check_v1 = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._check_v1", fake__check_v1
    )
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert newscap_checker._check_v1.call_count == 1


def test_newscap_checker__do_check_write_last_checked_time_to_file(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = json.loads(root_json_without_v2)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    monkeypatch.setattr("gridsync.news.NewscapChecker._check_v1", Mock())
    monkeypatch.setattr("time.time", lambda: 1234567890)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    with open(newscap_checker._last_checked_path) as f:
        assert f.read() == "1234567890"


root_json_v1_not_dirnode = """
[
 "dirnode",
 {
  "mutable": true,
  "verify_uri": "URI:DIR2-Verifier:mi3ac77qzzoclhakj3772cufxe:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "ro_uri": "URI:DIR2-RO:zjxovy5umhhbbzwn6gweo2jtg5:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "children": {
   "v1": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:i3epgjv2cjppjcoco2v7qlusmw:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "ro_uri": "URI:CHK:xnw2fjq7zmsw74bmwu7kdsffpn:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555017261.25157,
       "linkcrtime": 1555017261.25157
      }
     },
     "size": 90
    }
   ]
  }
 }
]
"""


def test_newscap_checker__do_check_log_warning_v1_not_dirnode(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = json.loads(root_json_v1_not_dirnode)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake__check_v1 = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._check_v1", fake__check_v1
    )
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert fake_logging_warning.call_count == 1


root_json_v1_not_found = """
[
 "dirnode",
 {
  "mutable": true,
  "verify_uri": "URI:DIR2-Verifier:mi3ac77qzzoclhakj3772cufxe:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "ro_uri": "URI:DIR2-RO:zjxovy5umhhbbzwn6gweo2jtg5:cz36ieckati5im53bfxu7pofqfbtjxwlly5cgloua6u3hr2tsghc",
  "children": {
   "test.txt": [
    "filenode",
    {
     "format": "CHK",
     "verify_uri": "URI:CHK-Verifier:i3epgjv2cjppjcoco2v7qlusmw:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "ro_uri": "URI:CHK:xnw2fjq7zmsw74bmwu7kdsffpn:tscqhsvpdu6ois3uizdfiu7qnjiapbifkx4p56iadgyyvq22ynda:1:1:90",
     "mutable": false,
     "metadata": {
      "tahoe": {
       "linkmotime": 1555017261.25157,
       "linkcrtime": 1555017261.25157
      }
     },
     "size": 90
    }
   ]
  }
 }
]
"""


def test_newscap_checker__do_check_log_warning_v1_not_found(
    newscap_checker, monkeypatch
):
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check", Mock()
    )
    monkeypatch.setattr("gridsync.tahoe.Tahoe.await_ready", Mock())
    content = json.loads(root_json_v1_not_found)
    monkeypatch.setattr("gridsync.tahoe.Tahoe.get_json", lambda x, y: content)
    fake__check_v1 = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._check_v1", fake__check_v1
    )
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    newscap_checker.gateway.newscap = "URI:NEWSCAP"
    newscap_checker._do_check()
    assert fake_logging_warning.call_count == 1


def test_newscap_checker__schedule_delayed_check_no_delay_use_randint(
    newscap_checker, monkeypatch, qtbot
):
    fake_deferLater = Mock()
    monkeypatch.setattr("gridsync.news.deferLater", fake_deferLater)
    monkeypatch.setattr("gridsync.news.randint", lambda x, y: 9999)
    newscap_checker._schedule_delayed_check()
    assert fake_deferLater.call_args[0][1] == 9999


def test_newscap_checker_start_idempotent(newscap_checker, monkeypatch):
    fake_schedule_delayed_check = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check",
        fake_schedule_delayed_check,
    )
    newscap_checker.start()
    newscap_checker.start()
    assert fake_schedule_delayed_check.call_count == 1


def test_newscap_checker_start_schedule_delayed_check_minimum_seconds(
    newscap_checker, monkeypatch
):
    fake_schedule_delayed_check = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check",
        fake_schedule_delayed_check,
    )
    newscap_checker.check_delay_min = 123
    newscap_checker.start()
    assert fake_schedule_delayed_check.call_args[0][0] == 123


def test_newscap_checker_start_schedule_delayed_check_random_seconds(
    newscap_checker, monkeypatch
):
    with open(newscap_checker._last_checked_path, "w") as f:
        f.write("100")
    fake_schedule_delayed_check = Mock()
    monkeypatch.setattr(
        "gridsync.news.NewscapChecker._schedule_delayed_check",
        fake_schedule_delayed_check,
    )
    monkeypatch.setattr("time.time", lambda: 110)
    newscap_checker.check_delay_min = 30
    newscap_checker.start()
    assert not fake_schedule_delayed_check.call_args[0]
