# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest
from wormhole.errors import WormholeError

from gridsync.errors import UpgradeRequiredError, TorError
from gridsync.wormhole_ import Wormhole, wormhole_receive, wormhole_send


@pytest.fixture(scope='module')
def wormhole():
    w = Wormhole()
    w._wormhole = MagicMock()
    return w


@pytest.inlineCallbacks
def test_wormhole_connect_emit_got_welcome_signal(qtbot, wormhole):
    wormhole._wormhole.get_welcome.return_value = {'current_cli_version': '0'}
    with qtbot.wait_signal(wormhole.got_welcome) as blocker:
        yield wormhole.connect()
    assert blocker.args == [{'current_cli_version': '0'}]


@pytest.inlineCallbacks
def test_wormhole_connect_use_tor(qtbot, monkeypatch, wormhole):
    kwargs_received = []

    def fake_create(*args, **kwargs):
        kwargs_received.append(kwargs)
        return wormhole._wormhole
    monkeypatch.setattr('gridsync.wormhole_.wormhole.create', fake_create)
    monkeypatch.setattr('gridsync.wormhole_.get_tor', lambda _: 'TorObject')
    wormhole._wormhole.get_welcome.return_value = {'current_cli_version': '0'}
    wormhole.use_tor = True
    yield wormhole.connect()
    assert kwargs_received == [{'tor': 'TorObject'}]
    wormhole.use_tor = False


@pytest.inlineCallbacks
def test_wormhole_use_tor_raise_tor_error(qtbot, monkeypatch, wormhole):
    monkeypatch.setattr('gridsync.wormhole_.get_tor', lambda _: None)
    wormhole.use_tor = True
    with pytest.raises(TorError):
        yield wormhole.connect()
    wormhole.use_tor = False


@pytest.inlineCallbacks
def test_wormhole_close_emit_closed_signal(qtbot, wormhole):
    with qtbot.wait_signal(wormhole.closed) as blocker:
        yield wormhole.close()
    assert blocker.args == []


@pytest.inlineCallbacks
def test_wormhole_close_emit_closed_signal_with_wormhole_error_pass(qtbot):
    wormhole = Wormhole()
    wormhole._wormhole = MagicMock()
    wormhole._wormhole.close = MagicMock(side_effect=WormholeError())
    with qtbot.wait_signal(wormhole.closed) as blocker:
        yield wormhole.close()
    assert blocker.args == []


@pytest.inlineCallbacks
def test_wormhole_receive_via_xfer_util(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"offer": {"message": "{\\"nickname\\": \\"Test Grid\\"}"}}'
    output = yield wormhole.receive('123-test-test')
    assert output == {"nickname": "Test Grid"}


@pytest.inlineCallbacks
def test_wormhole_receive_via_xfer_util_raise_unknown_offer(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"offer": {"NOT_message": "{\\"nickname\\": \\"Test Grid\\"}"}}'
    with pytest.raises(Exception):
        yield wormhole.receive('123-test-test')


@pytest.inlineCallbacks
def test_wormhole_receive_emit_got_introduction_signal(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"server-v1": {}}}'
    with qtbot.wait_signal(wormhole.got_introduction):
        yield wormhole.receive('123-test-test')


@pytest.inlineCallbacks
def test_wormhole_receive_raise_upgrade_required_no_abilities(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = b'{"blah": "blah"}'
    with pytest.raises(UpgradeRequiredError):
        yield wormhole.receive('123-test-test')


@pytest.inlineCallbacks
def test_wormhole_receive_raise_upgrade_required_bad_version(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"server-v9999": {}}}'
    with pytest.raises(UpgradeRequiredError):
        yield wormhole.receive('123-test-test')


@pytest.inlineCallbacks
def test_wormhole_receive_succeed_return_msg_dict(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"server-v1": {}}}'
    output = yield wormhole.receive('123-test-test')
    assert output == {'abilities': {'server-v1': {}}}


@pytest.inlineCallbacks
def test_wormhole_receive_succeed_emit_got_message_signal(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"offer": {"message": "{\\"nickname\\": \\"Test Grid\\"}"}}'
    with qtbot.wait_signal(wormhole.got_message) as blocker:
        yield wormhole.receive('123-test-test')
    assert blocker.args == [{'nickname': 'Test Grid'}]


@pytest.inlineCallbacks
def test_wormhole_send_emit_got_introduction_signal(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"client-v1": {}}}'
    with qtbot.wait_signal(wormhole.got_introduction):
        yield wormhole.send('Testing', '123-test-test')


@pytest.inlineCallbacks
def test_wormhole_send_raise_upgrade_required_no_abilities(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = b'{"blah": "blah"}'
    with pytest.raises(UpgradeRequiredError):
        yield wormhole.send('Testing', '123-test-test')


@pytest.inlineCallbacks
def test_wormhole_send_raise_upgrade_required_bad_version(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"server-v9999": {}}}'
    with pytest.raises(UpgradeRequiredError):
        yield wormhole.send('Testing', '123-test-test')


@pytest.inlineCallbacks
def test_wormhole_send_allocate_code_emit_got_code_signal(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"client-v1": {}}}'
    wormhole._wormhole.get_code.return_value = "9999-test-code"
    with qtbot.wait_signal(wormhole.got_code) as blocker:
        yield wormhole.send('Testing')
    assert blocker.args == ['9999-test-code']


@pytest.inlineCallbacks
def test_wormhole_send_succeed_emit_send_completed_signal(qtbot, wormhole):
    wormhole._wormhole.get_message.return_value = \
        b'{"abilities": {"client-v1": {}}}'
    with qtbot.wait_signal(wormhole.send_completed):
        yield wormhole.send('Testing')


@pytest.inlineCallbacks
def test_wormhole_receive_function(monkeypatch):
    monkeypatch.setattr(
        'gridsync.wormhole_.Wormhole.receive', lambda x, y: 'msg')
    output = yield wormhole_receive('123-test-test')
    assert output == 'msg'


@pytest.inlineCallbacks
def test_wormhole_send_function(monkeypatch):
    monkeypatch.setattr(
        'gridsync.wormhole_.Wormhole.send', lambda x, y, z: None)
    yield wormhole_send('123-test-test')
