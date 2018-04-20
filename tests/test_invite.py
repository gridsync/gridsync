# -*- coding: utf-8 -*-

import os
from unittest.mock import MagicMock

import pytest
from twisted.internet.defer import CancelledError
from wormhole.errors import (
    LonelyError, ServerConnectionError, WelcomeError, WormholeError,
    WrongPasswordError)

from gridsync.errors import UpgradeRequiredError
from gridsync.invite import (
    get_settings_from_cheatcode, is_valid, show_failure, Wormhole,
    wormhole_receive, wormhole_send)


@pytest.mark.parametrize("code,result", [
    ['topmost-vagabond', False],  # Not three words
    ['corporate-cowbell-commando', False],  # First word not digit
    ['2-tanooki-travesty', False],  # Second word not in wordlist
    ['3-eating-wasabi', False],  # Third word not in wordlist
    ['1-cranky-tapeworm', True]
])
def test_is_valid_code(code, result):
    assert is_valid(code) == result


def test_get_settings_from_cheatcode(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir')
    providers_path = os.path.join(pkgdir, 'resources', 'providers')
    os.makedirs(providers_path)
    with open(os.path.join(providers_path, 'test-test.json'), 'w') as f:
        f.write('{"introducer": "pb://"}')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    settings = get_settings_from_cheatcode('test-test')
    assert settings['introducer'] == 'pb://'


def test_get_settings_from_cheatcode_none(tmpdir_factory, monkeypatch):
    pkgdir = os.path.join(str(tmpdir_factory.getbasetemp()), 'pkgdir-empty')
    monkeypatch.setattr('gridsync.invite.pkgdir', pkgdir)
    assert get_settings_from_cheatcode('test-test') is None


@pytest.mark.parametrize("failure", [
    ServerConnectionError, WelcomeError, WrongPasswordError, LonelyError,
    UpgradeRequiredError, CancelledError, WormholeError])
def test_show_failure(failure, monkeypatch):
    monkeypatch.setattr('gridsync.invite.QMessageBox', MagicMock())

    def fake_failure(failure):
        f = MagicMock()
        f.type = failure
        return f
    show_failure(fake_failure(failure))


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
    monkeypatch.setattr('gridsync.invite.Wormhole.receive', lambda x, y: 'msg')
    output = yield wormhole_receive('123-test-test')
    assert output == 'msg'


@pytest.inlineCallbacks
def test_wormhole_send_function(monkeypatch):
    monkeypatch.setattr('gridsync.invite.Wormhole.send', lambda x, y, z: None)
    yield wormhole_send('123-test-test')
