from pytest_twisted import async_yield_fixture, inlineCallbacks
from twisted.internet import reactor
from twisted.internet.task import deferLater

from gridsync.supervisor import Supervisor
from gridsync.system import kill


@inlineCallbacks
def test_supervisor_writes_pid_to_pidfile(tmp_path):
    supervisor = Supervisor()
    pidfile = tmp_path / "python.pid"
    pid = yield supervisor.start(["python"], pidfile)
    assert int(pidfile.read_text()) == pid


@inlineCallbacks
def test_supervisor_restarts_process_when_killed(tmp_path):
    supervisor = Supervisor(restart_delay=0)
    pidfile = tmp_path / "python.pid"
    pid_1 = yield supervisor.start(["python"], pidfile)
    kill(pidfile=pidfile)
    yield deferLater(reactor, 0.1, lambda: None)
    pid_2 = int(pidfile.read_text())
    assert pid_1 != pid_2
