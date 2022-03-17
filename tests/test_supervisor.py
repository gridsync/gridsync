import sys

from psutil import Process
from pytest_twisted import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync.supervisor import Supervisor

PROCESS_ARGS = [sys.executable, "-c", "while True: print('OK')"]


@inlineCallbacks
def test_supervisor_sets_pid_attribute_on_start(tmp_path):
    supervisor = Supervisor()
    pid, _ = yield supervisor.start(PROCESS_ARGS)
    assert supervisor.pid == pid


@inlineCallbacks
def test_supervisor_sets_name_attribute_on_start(tmp_path):
    supervisor = Supervisor()
    _, name = yield supervisor.start(PROCESS_ARGS)
    assert supervisor.name == name


@inlineCallbacks
def test_supervisor_unsets_pid_attribute_on_stop(tmp_path):
    supervisor = Supervisor()
    pid, _ = yield supervisor.start(PROCESS_ARGS)
    pid_was_set = supervisor.pid == pid
    yield supervisor.stop()
    pid_was_unset = supervisor.pid is None
    assert pid_was_set and pid_was_unset


@inlineCallbacks
def test_supervisor_unsets_name_attribute_on_stop(tmp_path):
    supervisor = Supervisor()
    _, name = yield supervisor.start(PROCESS_ARGS)
    name_was_set = supervisor.name == name
    yield supervisor.stop()
    name_was_unset = supervisor.name == ""
    assert name_was_set and name_was_unset


@inlineCallbacks
def test_supervisor_writes_pid_to_pidfile_on_start(tmp_path):
    pidfile = tmp_path / "python.pid"
    supervisor = Supervisor(pidfile=pidfile)
    pid, _ = yield supervisor.start(PROCESS_ARGS)
    assert int(pidfile.read_text().split()[0]) == pid


@inlineCallbacks
def test_supervisor_writes_name_to_pidfile_on_start(tmp_path):
    pidfile = tmp_path / "python.pid"
    supervisor = Supervisor(pidfile=pidfile)
    _, name = yield supervisor.start(PROCESS_ARGS)
    assert " ".join(pidfile.read_text().split()[1:]) == name


@inlineCallbacks
def test_supervisor_removes_pidfile_on_stop(tmp_path):
    pidfile = tmp_path / "python.pid"
    supervisor = Supervisor(pidfile=pidfile)
    pid, _ = yield supervisor.start(PROCESS_ARGS)
    pidfile_was_written = int(pidfile.read_text().split()[0]) == pid
    yield supervisor.stop()
    pidfile_was_removed = not pidfile.exists()
    assert pidfile_was_written and pidfile_was_removed


@inlineCallbacks
def test_supervisor_restarts_process_when_killed(tmp_path):
    pidfile = tmp_path / "python.pid"
    supervisor = Supervisor(pidfile=pidfile, restart_delay=0)
    pid_1, _ = yield supervisor.start(PROCESS_ARGS, started_trigger="OK")
    Process(pid_1).kill()
    yield deferLater(reactor, 3, lambda: None)
    pid_2 = int(pidfile.read_text().split()[0])
    assert pid_1 != pid_2


@inlineCallbacks
def test_supervisor_does_not_restart_process_when_stopped(tmp_path):
    pidfile = tmp_path / "python.pid"
    supervisor = Supervisor(pidfile=pidfile, restart_delay=0)
    yield supervisor.start(PROCESS_ARGS, started_trigger="OK")
    yield supervisor.stop()
    yield deferLater(reactor, 0.5, lambda: None)
    assert supervisor.pid is None
