# -*- coding: utf-8 -*-

from __future__ import print_function

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # pylint: disable=import-error
import errno
import os
import signal
import sys
from io import BytesIO

from twisted.internet import reactor
from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.error import ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.python.procutils import which


if getattr(sys, 'frozen', False):
    os.environ["PATH"] += os.pathsep + os.path.join(
        os.path.dirname(sys.executable), 'Tahoe-LAFS')


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
        self.pidfile = os.path.join(self.nodedir, "twistd.pid")

    def config_set(self, section, option, value):
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.nodedir, 'tahoe.cfg'))
        config.set(section, option, value)
        with open(os.path.join(self.nodedir, 'tahoe.cfg'), 'w') as f:
            config.write(f)

    def config_get(self, section, option):
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.nodedir, 'tahoe.cfg'))
        return config.get(section, option)

    def line_received(self, line):
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
        #self.start_monitor()
