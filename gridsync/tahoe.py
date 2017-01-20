# -*- coding: utf-8 -*-

from __future__ import print_function

import errno
import os
import re
import signal
import sys
from io import BytesIO

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater
from twisted.python.procutils import which
from twisted.web.client import Agent, readBody

from gridsync.config import Config


def is_valid_furl(furl):
    if re.match(r'^pb://[a-z2-7]+@[a-zA-Z0-9\.:,-]+:\d+/[a-z2-7]+$', furl):
        return True
    else:
        return False


class CommandProtocol(ProcessProtocol):
    def __init__(self, parent, callback_trigger=None):
        self.parent = parent
        self.trigger = callback_trigger
        self.done = Deferred()
        self.output = BytesIO()

    def outReceived(self, data):
        self.output.write(data)
        data = data.decode('utf-8')
        for line in data.strip().split('\n'):
            self.parent.line_received(line)
            if not self.done.called and self.trigger and self.trigger in line:
                self.done.callback(self.transport.pid)

    def errReceived(self, data):
        self.outReceived(data)

    def processEnded(self, reason):
        if not self.done.called:
            self.done.callback(self.output.getvalue())

    def processExited(self, reason):
        if not self.done.called and not isinstance(reason.value, ProcessDone):
            self.done.errback(reason)


class Tahoe(object):
    def __init__(self, nodedir=None, executable=None):
        self.nodedir = nodedir
        self.executable = executable
        if not self.nodedir:
            self.nodedir = os.path.join(os.path.expanduser('~'), '.tahoe')
        self.config = Config(os.path.join(self.nodedir, 'tahoe.cfg'))
        self.pidfile = os.path.join(self.nodedir, 'twistd.pid')
        self.nodeurl = None
        self.shares_happy = None

    def config_set(self, section, option, value):
        self.config.set(section, option, value)

    def config_get(self, section, option):
        return self.config.get(section, option)

    def line_received(self, line):  # pylint: disable=no-self-use
        # TODO: Connect to Core via Qt signals/slots?
        print(">>> " + line)

    def _win32_popen(self, args, env, callback_trigger=None):
        # This is a workaround to prevent Command Prompt windows from opening
        # when spawning tahoe processes from the GUI on Windows, as Twisted's
        # reactor.spawnProcess() API does not allow Windows creation flags to
        # be passed to subprocesses. By passing 0x08000000 (CREATE_NO_WINDOW),
        # the opening of the Command Prompt window will be surpressed while
        # still allowing access to stdout/stderr. See:
        # https://twistedmatrix.com/pipermail/twisted-python/2007-February/014733.html
        import subprocess
        proc = subprocess.Popen(
            args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, creationflags=0x08000000)
        output = BytesIO()
        for line in iter(proc.stdout.readline, ''):
            output.write(line.encode('utf-8'))
            self.line_received(line.rstrip())
            if callback_trigger and callback_trigger in line.rstrip():
                return proc.pid
        proc.poll()
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, args)
        else:
            return output.getvalue()

    @inlineCallbacks
    def command(self, args, callback_trigger=None):
        exe = (self.executable if self.executable else which('tahoe')[0])
        args = [exe] + ['-d', self.nodedir] + args
        env = os.environ
        env['PYTHONUNBUFFERED'] = '1'
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            from twisted.internet.threads import deferToThread
            output = yield deferToThread(
                self._win32_popen, args, env, callback_trigger)
        else:
            protocol = CommandProtocol(self, callback_trigger)
            reactor.spawnProcess(protocol, exe, args=args, env=env)
            output = yield protocol.done
        returnValue(output)

    #@inlineCallbacks
    #def start_monitor(self):
    #    furl = os.path.join(self.nodedir, 'private', 'logport.furl')
    #    yield self.command(['debug', 'flogtool', 'tail', furl])

    def stop(self):
        if not os.path.isfile(self.pidfile):
            print('No "twistd.pid" file found in {}'.format(self.nodedir))
            return
        with open(self.pidfile, 'r') as f:
            pid = f.read()
        pid = int(pid)
        print("Trying to kill PID {}...".format(pid))
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as err:
            print(err)
            if err.errno == errno.ESRCH or err.errno == errno.EINVAL:
                os.remove(self.pidfile)
            else:
                raise

    @inlineCallbacks
    def start(self):
        if os.path.isfile(self.pidfile):
            self.stop()
        pid = yield self.command(['run'], 'client running')
        pid = str(pid)
        if sys.platform == 'win32' and pid.isdigit():
            with open(self.pidfile, 'w') as f:
                f.write(pid)
        with open(os.path.join(self.nodedir, 'node.url')) as f:
            self.nodeurl = f.read().strip()
        #self.start_monitor()

    @inlineCallbacks
    def get_connected_servers(self):
        agent = Agent(reactor)
        resp = yield agent.request('GET'.encode(), self.nodeurl.encode())
        if resp.code == 200:
            html = yield readBody(resp)
            match = re.search('Connected to <span>(.+?)</span>', html.decode())
            if match:
                returnValue(int(match.group(1)))

    @inlineCallbacks
    def is_ready(self):
        if not self.shares_happy:
            self.shares_happy = int(self.config_get('client', 'shares.happy'))
        connected_servers = yield self.get_connected_servers()
        if connected_servers >= self.shares_happy:
            returnValue(True)
        else:
            returnValue(False)

    @inlineCallbacks
    def await_ready(self):
        ready = yield self.is_ready()
        while not ready:
            yield deferLater(reactor, 0.2, lambda: None)
            ready = yield self.is_ready()
