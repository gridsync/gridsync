import sys

from pytest_twisted import inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync.supervisor import Supervisor
from gridsync.system import kill

PROCESS_ARGS = [sys.executable, "-c", "while True: print('OK')"]


@inlineCallbacks
def test_supervisor_writes_pid_to_pidfile(tmp_path):
    supervisor = Supervisor()
    pidfile = tmp_path / "python.pid"
    pid = yield supervisor.start(PROCESS_ARGS, pidfile)
    assert int(pidfile.read_text()) == pid


@inlineCallbacks
def test_supervisor_restarts_process_when_killed(tmp_path):
    supervisor = Supervisor(restart_delay=0)
    pidfile = tmp_path / "python.pid"
    pid_1 = yield supervisor.start(PROCESS_ARGS, pidfile, started_trigger="OK")
    kill(pidfile=pidfile)
    yield deferLater(reactor, 2, lambda: None)
    pid_2 = int(pidfile.read_text())
    assert pid_1 != pid_2


@inlineCallbacks
def test_supervisor_does_not_restart_process_when_stopped(tmp_path):
    supervisor = Supervisor(restart_delay=0)
    pidfile = tmp_path / "python.pid"
    yield supervisor.start(PROCESS_ARGS, pidfile, started_trigger="OK")
    supervisor.stop()
    yield deferLater(reactor, 0.5, lambda: None)
    assert pidfile.exists() is False
