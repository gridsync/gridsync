# -*- coding: utf-8 -*-

import errno
import json
import logging as log
import os
import re
import shutil
import signal
import sys
from io import BytesIO

import treq
from twisted.internet import reactor
from twisted.internet.defer import (
    Deferred, DeferredLock, gatherResults, inlineCallbacks, returnValue)
from twisted.internet.error import ConnectError, ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater
from twisted.python.procutils import which

from gridsync.config import Config
from gridsync.errors import NodedirExistsError


def is_valid_furl(furl):
    return re.match(r'^pb://[a-z2-7]+@[a-zA-Z0-9\.:,-]+:\d+/[a-z2-7]+$', furl)


def get_nodedirs(basedir):
    nodedirs = []
    try:
        for filename in os.listdir(basedir):
            filepath = os.path.join(basedir, filename)
            confpath = os.path.join(filepath, 'tahoe.cfg')
            if os.path.isdir(filepath) and os.path.isfile(confpath):
                log.debug("Found nodedir: %s", filepath)
                nodedirs.append(filepath)
    except OSError:
        pass
    return sorted(nodedirs)


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
            if line:
                self.parent.line_received(line)
            if not self.done.called and self.trigger and self.trigger in line:
                self.done.callback(self.transport.pid)

    def errReceived(self, data):
        self.outReceived(data)

    def processEnded(self, reason):
        if not self.done.called:
            self.done.callback(self.output.getvalue().decode('utf-8'))

    def processExited(self, reason):
        if not self.done.called and not isinstance(reason.value, ProcessDone):
            self.done.errback(reason)


class Tahoe(object):  # pylint: disable=too-many-public-methods
    def __init__(self, nodedir=None, executable=None):
        self.executable = executable
        if nodedir:
            self.nodedir = os.path.expanduser(nodedir)
        else:
            self.nodedir = os.path.join(os.path.expanduser('~'), '.tahoe')
        self.rootcap_path = os.path.join(self.nodedir, 'private', 'rootcap')
        self.config = Config(os.path.join(self.nodedir, 'tahoe.cfg'))
        self.pidfile = os.path.join(self.nodedir, 'twistd.pid')
        self.nodeurl = None
        self.shares_happy = None
        self.name = os.path.basename(self.nodedir)
        self.api_token = None
        self.magic_folders_dir = os.path.join(self.nodedir, 'magic-folders')
        self.magic_folders = []
        self.magic_folder_dircap = None
        self.magic_folder_nickname = None
        self.magic_folder_path = None
        self.collective_dircap = None
        self.lock = DeferredLock()

    def config_set(self, section, option, value):
        self.config.set(section, option, value)

    def config_get(self, section, option):
        return self.config.get(section, option)

    def get_settings(self):
        settings = {
            'nickname': self.name,
            'introducer': self.config_get('client', 'introducer.furl'),
            'shares-needed': self.config_get('client', 'shares.needed'),
            'shares-happy': self.config_get('client', 'shares.happy'),
            'shares-total': self.config_get('client', 'shares.total')
        }
        icon_path = os.path.join(self.nodedir, 'icon')
        icon_url_path = icon_path + '.url'
        if os.path.exists(icon_url_path):
            with open(icon_url_path) as f:
                settings['icon_url'] = f.read().strip()
        # XXX: Support 'icon_base64'?
        return settings

    def get_aliases(self):
        aliases = {}
        aliases_file = os.path.join(self.nodedir, 'private', 'aliases')
        try:
            with open(aliases_file) as f:
                for line in f.readlines():
                    if not line.startswith('#'):
                        try:
                            name, cap = line.split(':', 1)
                            aliases[name + ':'] = cap.strip()
                        except ValueError:
                            pass
            return aliases
        except IOError:
            return

    def get_alias(self, alias):
        if not alias.endswith(':'):
            alias = alias + ':'
        try:
            for name, cap in self.get_aliases().items():
                if name == alias:
                    return cap
        except AttributeError:
            return

    def line_received(self, line):
        # TODO: Connect to Core via Qt signals/slots?
        log.debug("[%s] >>> %s", self.name, line)

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
            return str(output.getvalue())

    @inlineCallbacks
    def command(self, args, callback_trigger=None):
        exe = (self.executable if self.executable else which('tahoe')[0])
        args = [exe] + ['-d', self.nodedir] + args
        env = os.environ
        env['PYTHONUNBUFFERED'] = '1'
        log.debug("Executing: %s", ' '.join(args))
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            from twisted.internet.threads import deferToThread
            output = yield deferToThread(
                self._win32_popen, args, env, callback_trigger)
        else:
            protocol = CommandProtocol(self, callback_trigger)
            reactor.spawnProcess(protocol, exe, args=args, env=env)
            output = yield protocol.done
        returnValue(output)

    @inlineCallbacks
    def version(self):
        output = yield self.command(['--version'])
        returnValue((self.executable, output.split()[1]))

    @inlineCallbacks
    def create_client(self, **kwargs):
        if os.path.exists(self.nodedir):
            raise NodedirExistsError
        valid_kwargs = ('nickname', 'introducer', 'shares-needed',
                        'shares-happy', 'shares-total')
        args = ['create-client', '--webport=tcp:0:interface=127.0.0.1']
        for key, value in kwargs.items():
            if key in valid_kwargs:
                args.extend(['--{}'.format(key), str(value)])
            elif key in ['needed', 'happy', 'total']:
                args.extend(['--shares-{}'.format(key), str(value)])
        yield self.command(args)

    @inlineCallbacks
    def stop(self):
        if not os.path.isfile(self.pidfile):
            log.error('No "twistd.pid" file found in %s', self.nodedir)
            return
        elif sys.platform == 'win32':
            with open(self.pidfile, 'r') as f:
                pid = f.read()
            pid = int(pid)
            log.debug("Trying to kill PID %d...", pid)
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as err:
                if err.errno not in (errno.ESRCH, errno.EINVAL):
                    log.error(err)
            os.remove(self.pidfile)
        else:
            yield self.command(['stop'])
        yield self.stop_magic_folders()  # XXX: Move to Core? gatherResults?

    @inlineCallbacks
    def start(self):
        if os.path.isfile(self.pidfile):
            yield self.stop()
        pid = yield self.command(['run'], 'client running')
        pid = str(pid)
        if sys.platform == 'win32' and pid.isdigit():
            with open(self.pidfile, 'w') as f:
                f.write(pid)
        with open(os.path.join(self.nodedir, 'node.url')) as f:
            self.nodeurl = f.read().strip()
        token_file = os.path.join(self.nodedir, 'private', 'api_auth_token')
        with open(token_file) as f:
            self.api_token = f.read().strip()
        self.shares_happy = int(self.config_get('client', 'shares.happy'))
        self.magic_folder_path = self.config_get(
            'magic_folder', 'local.directory')
        yield self.start_magic_folders()  # XXX: Move to Core? gatherResults?

    @inlineCallbacks
    def get_connected_servers(self):
        if not self.nodeurl:
            return
        try:
            resp = yield treq.get(self.nodeurl)
        except ConnectError:
            return
        if resp.code == 200:
            html = yield treq.content(resp)
            match = re.search(
                'Connected to <span>(.+?)</span>', html.decode('utf-8'))
            if match:
                returnValue(int(match.group(1)))

    @inlineCallbacks
    def is_ready(self):
        if not self.shares_happy:
            returnValue(False)
        connected_servers = yield self.get_connected_servers()
        if not connected_servers:
            returnValue(False)
        elif connected_servers >= self.shares_happy:
            returnValue(True)
        else:
            returnValue(False)

    @inlineCallbacks
    def await_ready(self):
        # TODO: Replace with "readiness" API?
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2844
        ready = yield self.is_ready()
        while not ready:
            yield deferLater(reactor, 0.2, lambda: None)
            ready = yield self.is_ready()

    @inlineCallbacks
    def mkdir(self):
        resp = yield treq.post(self.nodeurl + 'uri', params={'t': 'mkdir'})
        if resp.code == 200:
            content = yield treq.content(resp)
            returnValue(content.decode('utf-8').strip())
        else:
            raise Exception(
                "Error creating Tahoe-LAFS directory: {}".format(resp.code))

    @inlineCallbacks
    def create_rootcap(self):
        log.debug("Creating rootcap...")
        if os.path.exists(self.rootcap_path):
            raise OSError(
                "Rootcap file already exists: {}".format(self.rootcap_path))
        rootcap = yield self.mkdir()
        with open(self.rootcap_path, 'w') as f:
            f.write(rootcap)
        log.debug("Rootcap saved to file: %s", self.rootcap_path)

    @inlineCallbacks
    def link(self, dircap, childname, childcap):
        lock = yield self.lock.acquire()
        resp = yield treq.post(
            '{}uri/{}/?t=uri&name={}&uri={}'.format(
                self.nodeurl, dircap, childname, childcap))
        yield lock.release()
        if resp.code != 200:
            content = yield treq.content(resp)
            raise Exception(content.decode('utf-8'))

    @inlineCallbacks
    def create_magic_folder(self, path):
        # Because Tahoe-LAFS doesn't currently support having multiple
        # magic-folders per tahoe client, create the magic-folder inside
        # a new nodedir using the current nodedir's connection settings.
        # See https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2792
        try:
            os.makedirs(self.magic_folders_dir)
        except OSError:
            pass
        path = os.path.realpath(os.path.expanduser(path))
        try:
            os.makedirs(path)
        except OSError:
            pass
        basename = os.path.basename(path)
        magic_folder = Tahoe(
            os.path.join(self.magic_folders_dir, basename),
            executable=self.executable)
        self.magic_folders.append(magic_folder)
        settings = {
            'nickname': self.config_get('node', 'nickname'),
            'introducer': self.config_get('client', 'introducer.furl'),
            'shares-needed': self.config_get('client', 'shares.needed'),
            'shares-happy': self.config_get('client', 'shares.happy'),
            'shares-total': self.config_get('client', 'shares.total')
        }
        yield magic_folder.create_client(**settings)
        yield magic_folder.start()
        yield magic_folder.await_ready()
        yield magic_folder.command(
            ['magic-folder', 'create', 'magic:', 'admin', path])
        yield magic_folder.stop()
        yield magic_folder.start()

        rootcap = self.read_cap_from_file(self.rootcap_path)
        yield self.link(rootcap, basename + ' (collective)',
                        magic_folder.get_alias('magic'))
        yield self.link(rootcap, basename + ' (personal)',
                        magic_folder.get_magic_folder_dircap())

    @inlineCallbacks
    def magic_folder_invite(self, nickname):
        code = yield self.command(
            ['magic-folder', 'invite', 'magic:', nickname])
        returnValue(code.strip())

    @inlineCallbacks
    def start_magic_folders(self):
        tasks = []
        for nodedir in get_nodedirs(self.magic_folders_dir):
            magic_folder = Tahoe(nodedir, executable=self.executable)
            self.magic_folders.append(magic_folder)
            tasks.append(magic_folder.start())
        yield gatherResults(tasks)

    @inlineCallbacks
    def stop_magic_folders(self):
        tasks = []
        for nodedir in get_nodedirs(self.magic_folders_dir):
            tasks.append(Tahoe(nodedir, executable=self.executable).stop())
        yield gatherResults(tasks)

    @inlineCallbacks
    def remove_magic_folder(self, name):
        for magic_folder in self.magic_folders:
            if magic_folder.name == name:
                self.magic_folders.remove(magic_folder)
                yield magic_folder.stop()
                shutil.rmtree(magic_folder.nodedir, ignore_errors=True)

    @inlineCallbacks
    def get_magic_folder_status(self):
        if not self.nodeurl or not self.api_token:
            return
        uri = self.nodeurl + 'magic_folder'
        try:
            resp = yield treq.post(uri, {'token': self.api_token, 't': 'json'})
        except ConnectError:
            return
        if resp.code == 200:
            content = yield treq.content(resp)
            returnValue(json.loads(content.decode('utf-8')))

    @inlineCallbacks
    def get_json(self, cap):
        if not cap or not self.nodeurl:
            return
        uri = '{}uri/{}/?t=json'.format(self.nodeurl, cap)
        try:
            resp = yield treq.get(uri)
        except ConnectError:
            return
        if resp.code == 200:
            content = yield treq.content(resp)
            returnValue(json.loads(content.decode('utf-8')))

    @staticmethod
    def read_cap_from_file(filepath):
        try:
            with open(filepath) as f:
                cap = f.read().strip()
        except OSError:
            return
        return cap

    def get_collective_dircap(self):
        if not self.collective_dircap:
            path = os.path.join(self.nodedir, 'private', 'collective_dircap')
            self.collective_dircap = self.read_cap_from_file(path)
        return self.collective_dircap

    def get_magic_folder_dircap(self):
        if not self.magic_folder_dircap:
            path = os.path.join(self.nodedir, 'private', 'magic_folder_dircap')
            self.magic_folder_dircap = self.read_cap_from_file(path)
        return self.magic_folder_dircap

    @inlineCallbacks
    def get_magic_folder_members(self, content=None):
        if not content:
            content = yield self.get_json(self.get_collective_dircap())
        if content:
            members = []
            children = content[1]['children']
            if not self.magic_folder_dircap:
                self.get_magic_folder_dircap()
            for member in children:
                readcap = children[member][1]['ro_uri']
                if self.magic_folder_dircap:
                    my_fingerprint = self.magic_folder_dircap.split(':')[-1]
                    fingerprint = readcap.split(':')[-1]
                    if fingerprint == my_fingerprint:
                        self.magic_folder_nickname = member
                        members.insert(0, (member, readcap))
                    else:
                        members.append((member, readcap))
                else:
                    members.append((member, readcap))
            returnValue(members)

    @staticmethod
    def size_from_content(content):
        size = 0
        filenodes = content[1]['children']
        for filenode in filenodes:
            size += int(filenodes[filenode][1]['size'])
        return size

    @inlineCallbacks
    def get_magic_folder_size(self, content=None):
        if not content:
            content = yield self.get_json(self.get_magic_folder_dircap())
        if content:
            returnValue(self.size_from_content(content))

    @inlineCallbacks
    def get_magic_folder_info(self, members=None):
        total_size = 0
        sizes_dict = {}
        if not members:
            members = yield self.get_magic_folder_members()
        if members:
            for member, dircap in reversed(members):
                sizes_dict[member] = {}
                json_data = yield self.get_json(dircap)
                children = json_data[1]['children']
                for filenode in children:
                    filepath = filenode.replace('@_', os.path.sep)
                    try:
                        size = int(children[filenode][1]['size'])
                    except KeyError:  # if linked manually
                        continue
                    sizes_dict[member][filepath] = size
                    total_size += size
        returnValue((members, total_size, sizes_dict))
