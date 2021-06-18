import errno
import signal
from unittest.mock import Mock

import pytest

from gridsync.system import kill


def test_kill_uses_SIGTERM(monkeypatch):
    fake_kill = Mock()
    monkeypatch.setattr("os.kill", fake_kill)
    kill(999999999)
    assert fake_kill.call_args[0] == (999999999, signal.SIGTERM)


def test_kill_from_pidfile(monkeypatch, tmp_path_factory):
    fake_kill = Mock()
    monkeypatch.setattr("os.kill", fake_kill)
    pidfile = tmp_path_factory.mktemp("test") / "pidfile.pid"
    pidfile.write_text("999999999")
    kill(pidfile=pidfile)
    assert fake_kill.call_args[0] == (999999999, signal.SIGTERM)


def test_kill_log_read_text_errors(monkeypatch, tmp_path_factory):
    fake_read_text = Mock(side_effect=EnvironmentError)
    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)
    fake_logging_error = Mock()
    monkeypatch.setattr("logging.error", fake_logging_error)
    pidfile = tmp_path_factory.mktemp("test") / "pidfile.pid"
    pidfile.write_text("999999999")
    kill(pidfile=pidfile)
    assert fake_logging_error.call_args[0][0].startswith("Error loading")


def test_kill_log_os_kill_errors(monkeypatch):
    monkeypatch.setattr("os.kill", Mock(side_effect=OSError(errno.ESRCH, "")))
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    kill(999999999)
    assert fake_logging_warning.call_args[0][0].startswith("Could not kill")


def test_kill_raise_unexpected_os_kill_errors(monkeypatch):
    monkeypatch.setattr("os.kill", Mock(side_effect=OSError))
    fake_logging_error = Mock()
    monkeypatch.setattr("logging.error", fake_logging_error)
    with pytest.raises(OSError):
        kill(999999999)


def test_kill_remove_pidfile(monkeypatch, tmp_path_factory):
    monkeypatch.setattr("os.kill", Mock(side_effect=OSError(errno.ESRCH, "")))
    pidfile = tmp_path_factory.mktemp("test") / "pidfile.pid"
    pidfile.write_text("999999999")
    exists_before = pidfile.exists()
    kill(pidfile=pidfile)
    exists_after = pidfile.exists()
    assert (exists_before, exists_after) == (True, False)


def test_kill_remove_pidfile_log_unlink_errors(monkeypatch, tmp_path_factory):
    monkeypatch.setattr("os.kill", Mock(side_effect=OSError(errno.ESRCH, "")))
    monkeypatch.setattr("pathlib.Path.unlink", Mock(side_effect=OSError))
    fake_logging_warning = Mock()
    monkeypatch.setattr("logging.warning", fake_logging_warning)
    pidfile = tmp_path_factory.mktemp("test") / "pidfile.pid"
    pidfile.write_text("999999999")
    kill(pidfile=pidfile)
    assert fake_logging_warning.call_args[0][0].startswith("Error removing")
