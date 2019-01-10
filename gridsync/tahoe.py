# -*- coding: utf-8 -*-

import errno
import hashlib
import json
import logging as log
import os
import re
import shutil
import signal
import sys
import tempfile
from collections import defaultdict, OrderedDict
from io import BytesIO


import treq
from twisted.internet import reactor
from twisted.internet.defer import (
    Deferred, DeferredList, DeferredLock, inlineCallbacks)
from twisted.internet.error import ConnectError, ProcessDone
from twisted.internet.protocol import ProcessProtocol
from twisted.internet.task import deferLater
from twisted.python.procutils import which
import yaml

from gridsync import pkgdir
from gridsync.config import Config
from gridsync.errors import TahoeError, TahoeCommandError, TahoeWebError
from gridsync.monitor import Monitor
from gridsync.preferences import set_preference, get_preference


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
            self.done.errback(
                TahoeCommandError(
                    self.output.getvalue().decode('utf-8').strip()))


class Tahoe():
    def __init__(self, nodedir=None, executable=None):
        self.executable = executable
        self.multi_folder_support = True
        if nodedir:
            self.nodedir = os.path.expanduser(nodedir)
        else:
            self.nodedir = os.path.join(os.path.expanduser('~'), '.tahoe')
        self.rootcap_path = os.path.join(self.nodedir, 'private', 'rootcap')
        self.servers_yaml_path = os.path.join(
            self.nodedir, 'private', 'servers.yaml')
        self.config = Config(os.path.join(self.nodedir, 'tahoe.cfg'))
        self.pidfile = os.path.join(self.nodedir, 'twistd.pid')
        self.nodeurl = None
        self.shares_happy = None
        self.name = os.path.basename(self.nodedir)
        self.api_token = None
        self.magic_folders_dir = os.path.join(self.nodedir, 'magic-folders')
        self.lock = DeferredLock()
        self.rootcap = None
        self.magic_folders = defaultdict(dict)
        self.remote_magic_folders = defaultdict(dict)
        self.use_tor = False
        self.monitor = Monitor(self)
        self._monitor_started = False

    def config_set(self, section, option, value):
        self.config.set(section, option, value)

    def config_get(self, section, option):
        return self.config.get(section, option)

    def get_settings(self, include_rootcap=False):
        settings = {
            'nickname': self.name,
            'shares-needed': self.config_get('client', 'shares.needed'),
            'shares-happy': self.config_get('client', 'shares.happy'),
            'shares-total': self.config_get('client', 'shares.total')
        }
        introducer = self.config_get('client', 'introducer.furl')
        if introducer:
            settings['introducer'] = introducer
        storage_servers = self.get_storage_servers()
        if storage_servers:
            settings['storage'] = storage_servers
        icon_path = os.path.join(self.nodedir, 'icon')
        icon_url_path = icon_path + '.url'
        if os.path.exists(icon_url_path):
            with open(icon_url_path) as f:
                settings['icon_url'] = f.read().strip()
        if include_rootcap and os.path.exists(self.rootcap_path):
            settings['rootcap'] = self.read_cap_from_file(self.rootcap_path)
        # TODO: Verify integrity? Support 'icon_base64'?
        return settings

    def export(self, dest, include_rootcap=False):
        log.debug("Exporting settings to '%s'...", dest)
        settings = self.get_settings(include_rootcap)
        if self.use_tor:
            settings['hide-ip'] = True
        with open(dest, 'w') as f:
            f.write(json.dumps(settings))
        log.debug("Exported settings to '%s'", dest)

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
            return aliases

    def get_alias(self, alias):
        if not alias.endswith(':'):
            alias = alias + ':'
        try:
            for name, cap in self.get_aliases().items():
                if name == alias:
                    return cap
            return None
        except AttributeError:
            return None

    def _set_alias(self, alias, cap=None):
        if not alias.endswith(':'):
            alias = alias + ':'
        aliases = self.get_aliases()
        if cap:
            aliases[alias] = cap
        else:
            try:
                del aliases[alias]
            except (KeyError, TypeError):
                return
        tmp_aliases_file = os.path.join(self.nodedir, 'private', 'aliases.tmp')
        with open(tmp_aliases_file, 'w') as f:
            data = ''
            for name, dircap in aliases.items():
                data += '{} {}\n'.format(name, dircap)
            f.write(data)
        aliases_file = os.path.join(self.nodedir, 'private', 'aliases')
        shutil.move(tmp_aliases_file, aliases_file)

    def add_alias(self, alias, cap):
        self._set_alias(alias, cap)

    def remove_alias(self, alias):
        self._set_alias(alias)

    def _read_servers_yaml(self):
        try:
            with open(self.servers_yaml_path) as f:
                return yaml.safe_load(f)
        except OSError:
            return {}

    def get_storage_servers(self):
        yaml_data = self._read_servers_yaml()
        if not yaml_data:
            return {}
        storage = yaml_data.get('storage')
        if not storage or not isinstance(storage, dict):
            return {}
        results = {}
        for server, server_data in storage.items():
            ann = server_data.get('ann')
            if not ann:
                continue
            results[server] = {
                'anonymous-storage-FURL': ann.get('anonymous-storage-FURL')
            }
            nickname = ann.get('nickname')
            if nickname:
                results[server]['nickname'] = nickname
        return results

    def add_storage_server(self, server_id, furl, nickname=None):
        log.debug("Adding storage server: %s...", server_id)
        yaml_data = self._read_servers_yaml()
        if not yaml_data or not yaml_data.get('storage'):
            yaml_data['storage'] = {}
        yaml_data['storage'][server_id] = {
            'ann': {'anonymous-storage-FURL': furl}
        }
        if nickname:
            yaml_data['storage'][server_id]['ann']['nickname'] = nickname
        with open(self.servers_yaml_path + '.tmp', 'w') as f:
            f.write(yaml.safe_dump(yaml_data, default_flow_style=False))
        shutil.move(self.servers_yaml_path + '.tmp', self.servers_yaml_path)
        log.debug("Added storage server: %s", server_id)

    def add_storage_servers(self, storage_servers):
        for server_id, data in storage_servers.items():
            nickname = data.get('nickname')
            furl = data.get('anonymous-storage-FURL')
            if furl:
                self.add_storage_server(server_id, furl, nickname)
            else:
                log.warning("No storage fURL provided for %s!", server_id)

    def load_magic_folders(self):
        data = {}
        yaml_path = os.path.join(self.nodedir, 'private', 'magic_folders.yaml')
        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
        except OSError:
            pass
        folders_data = data.get('magic-folders')
        if folders_data:
            for key, value in folders_data.items():  # to preserve defaultdict
                self.magic_folders[key] = value
        for folder in self.magic_folders:
            admin_dircap = self.get_admin_dircap(folder)
            if admin_dircap:
                self.magic_folders[folder]['admin_dircap'] = admin_dircap
        return self.magic_folders

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
            raise TahoeCommandError(str(output.getvalue()).strip())
        else:
            return str(output.getvalue()).strip()

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
        return output

    @inlineCallbacks
    def get_features(self):
        try:
            yield self.command(['magic-folder', 'list'])
        except TahoeCommandError as err:
            if str(err).strip().endswith('Unknown command: list'):
                # Has magic-folder support but no multi-magic-folder support
                return self.executable, True, False
            # Has no magic-folder support ('Unknown command: magic-folder')
            # or something else went wrong; consider executable unsupported
            return self.executable, False, False
        #if output:
        # Has magic-folder support and multi-magic-folder support
        return self.executable, True, True

    @inlineCallbacks
    def create_client(self, **kwargs):
        if os.path.exists(self.nodedir):
            raise FileExistsError(
                "Nodedir already exists: {}".format(self.nodedir))
        args = ['create-client', '--webport=tcp:0:interface=127.0.0.1']
        for key, value in kwargs.items():
            if key in ('nickname', 'introducer', 'shares-needed',
                       'shares-happy', 'shares-total'):
                args.extend(['--{}'.format(key), str(value)])
            elif key in ['needed', 'happy', 'total']:
                args.extend(['--shares-{}'.format(key), str(value)])
            elif key == 'hide-ip':
                args.append('--hide-ip')
        yield self.command(args)
        storage_servers = kwargs.get('storage')
        if storage_servers and isinstance(storage_servers, dict):
            self.add_storage_servers(storage_servers)

    def kill(self):
        try:
            with open(self.pidfile, 'r') as f:
                pid = int(f.read())
        except (EnvironmentError, ValueError) as err:
            log.warning("Error loading pid from pidfile: %s", str(err))
            return
        log.debug("Trying to kill PID %d...", pid)
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as err:
            if err.errno not in (errno.ESRCH, errno.EINVAL):
                log.error(err)

    @inlineCallbacks
    def stop(self):
        if not os.path.isfile(self.pidfile):
            log.error('No "twistd.pid" file found in %s', self.nodedir)
            return
        if sys.platform == 'win32':
            self.kill()
        else:
            try:
                yield self.command(['stop'])
            except TahoeCommandError:  # Process already dead/not running
                pass
        try:
            os.remove(self.pidfile)
        except EnvironmentError:
            pass

    @inlineCallbacks
    def upgrade_legacy_config(self):
        log.debug("Upgrading legacy configuration layout..")
        nodedirs = get_nodedirs(self.magic_folders_dir)
        if not nodedirs:
            log.warning("No nodedirs found; returning.")
            return
        magic_folders = {}
        for nodedir in nodedirs:
            basename = os.path.basename(nodedir)
            log.debug("Migrating configuration for '%s'...", basename)

            tahoe = Tahoe(nodedir)
            directory = tahoe.config_get('magic_folder', 'local.directory')
            poll_interval = tahoe.config_get('magic_folder', 'poll_interval')

            collective_dircap = self.read_cap_from_file(
                os.path.join(nodedir, 'private', 'collective_dircap'))
            magic_folder_dircap = self.read_cap_from_file(
                os.path.join(nodedir, 'private', 'magic_folder_dircap'))

            magic_folders[basename] = {
                'collective_dircap': collective_dircap,
                'directory': directory,
                'poll_interval': poll_interval,
                'upload_dircap': magic_folder_dircap
            }

            db_src = os.path.join(nodedir, 'private', 'magicfolderdb.sqlite')
            db_fname = ''.join(['magicfolder_', basename, '.sqlite'])
            db_dest = os.path.join(self.nodedir, 'private', db_fname)
            log.debug("Copying %s to %s...", db_src, db_dest)
            shutil.copyfile(db_src, db_dest)

            collective_dircap_rw = tahoe.get_alias('magic')
            if collective_dircap_rw:
                alias = hashlib.sha256(basename.encode()).hexdigest() + ':'
                yield self.command(
                    ['add-alias', alias, collective_dircap_rw])

        yaml_path = os.path.join(self.nodedir, 'private', 'magic_folders.yaml')
        log.debug("Writing magic-folder configs to %s...", yaml_path)
        with open(yaml_path, 'w') as f:
            f.write(yaml.safe_dump({'magic-folders': magic_folders}))

        log.debug("Backing up legacy configuration...")
        shutil.move(self.magic_folders_dir, self.magic_folders_dir + '.backup')

        log.debug("Enabling magic-folder for %s...", self.nodedir)
        self.config_set('magic_folder', 'enabled', 'True')

        log.debug("Finished upgrading legacy configuration")

    @inlineCallbacks
    def start(self):
        if not self._monitor_started:
            self.monitor.start()
            self._monitor_started = True
        tcp = self.config_get('connections', 'tcp')
        if tcp and tcp.lower() == 'tor':
            self.use_tor = True
        if os.path.isfile(self.pidfile):
            yield self.stop()
        if self.multi_folder_support and os.path.isdir(self.magic_folders_dir):
            yield self.upgrade_legacy_config()
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
        self.load_magic_folders()

    @inlineCallbacks
    def restart(self):
        log.debug("Restarting %s client...", self.name)
        # Temporarily disable desktop notifications for (dis)connect events
        pref = get_preference('notifications', 'connection')
        set_preference('notifications', 'connection', 'false')
        yield self.stop()
        yield self.start()
        yield self.await_ready()
        yield deferLater(reactor, 1, lambda: None)
        set_preference('notifications', 'connection', pref)
        log.debug("Finished restarting %s client.", self.name)

    @inlineCallbacks
    def get_grid_status(self):
        if not self.nodeurl:
            return None
        try:
            resp = yield treq.get(self.nodeurl + '?t=json')
        except ConnectError:
            return None
        if resp.code == 200:
            content = yield treq.content(resp)
            content = json.loads(content.decode('utf-8'))
            servers_connected = 0
            servers_known = 0
            available_space = 0
            if 'servers' in content:
                servers = content['servers']
                servers_known = len(servers)
                for server in servers:
                    if server['connection_status'].startswith('Connected'):
                        servers_connected += 1
                        if server['available_space']:
                            available_space += server['available_space']
            return servers_connected, servers_known, available_space
        return None

    @inlineCallbacks
    def get_connected_servers(self):
        if not self.nodeurl:
            return None
        try:
            resp = yield treq.get(self.nodeurl)
        except ConnectError:
            return None
        if resp.code == 200:
            html = yield treq.content(resp)
            match = re.search(
                'Connected to <span>(.+?)</span>', html.decode('utf-8'))
            if match:
                return int(match.group(1))
        return None

    @inlineCallbacks
    def is_ready(self):
        if not self.shares_happy:
            return False
        connected_servers = yield self.get_connected_servers()
        return bool(
            connected_servers and connected_servers >= self.shares_happy)

    @inlineCallbacks
    def await_ready(self):
        # TODO: Replace with "readiness" API?
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2844
        ready = yield self.is_ready()
        while not ready:
            yield deferLater(reactor, 0.2, lambda: None)
            ready = yield self.is_ready()

    @inlineCallbacks
    def mkdir(self, parentcap=None, childname=None):
        url = self.nodeurl + 'uri'
        params = {'t': 'mkdir'}
        if parentcap and childname:
            url += '/' + parentcap
            params['name'] = childname
        resp = yield treq.post(url, params=params)
        if resp.code == 200:
            content = yield treq.content(resp)
            return content.decode('utf-8').strip()
        raise TahoeWebError(
            "Error creating Tahoe-LAFS directory: {}".format(resp.code))

    @inlineCallbacks
    def create_rootcap(self):
        log.debug("Creating rootcap...")
        if os.path.exists(self.rootcap_path):
            raise OSError(
                "Rootcap file already exists: {}".format(self.rootcap_path))
        self.rootcap = yield self.mkdir()
        with open(self.rootcap_path, 'w') as f:
            f.write(self.rootcap)
        log.debug("Rootcap saved to file: %s", self.rootcap_path)
        return self.rootcap

    @inlineCallbacks
    def upload(self, local_path):
        log.debug("Uploading %s...", local_path)
        with open(local_path, 'rb') as f:
            resp = yield treq.put('{}uri'.format(self.nodeurl), f)
        if resp.code == 200:
            content = yield treq.content(resp)
            log.debug("Successfully uploaded %s", local_path)
            return content.decode('utf-8')
        content = yield treq.content(resp)
        raise TahoeWebError(content.decode('utf-8'))

    @inlineCallbacks
    def download(self, cap, local_path):
        log.debug("Downloading %s...", local_path)
        resp = yield treq.get('{}uri/{}'.format(self.nodeurl, cap))
        if resp.code == 200:
            with open(local_path, 'wb') as f:
                yield treq.collect(resp, f.write)
            log.debug("Successfully downloaded %s", local_path)
        else:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode('utf-8'))

    @inlineCallbacks
    def link(self, dircap, childname, childcap):
        lock = yield self.lock.acquire()
        try:
            resp = yield treq.post(
                '{}uri/{}/?t=uri&name={}&uri={}'.format(
                    self.nodeurl, dircap, childname, childcap))
        finally:
            yield lock.release()
        if resp.code != 200:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode('utf-8'))

    @inlineCallbacks
    def unlink(self, dircap, childname):
        lock = yield self.lock.acquire()
        try:
            resp = yield treq.post(
                '{}uri/{}/?t=unlink&name={}'.format(
                    self.nodeurl, dircap, childname))
        finally:
            yield lock.release()
        if resp.code != 200:
            content = yield treq.content(resp)
            raise TahoeWebError(content.decode('utf-8'))

    @inlineCallbacks
    def link_magic_folder_to_rootcap(self, name):
        log.debug("Linking folder '%s' to rootcap...", name)
        rootcap = self.get_rootcap()
        admin_dircap = self.get_admin_dircap(name)
        if admin_dircap:
            yield self.link(rootcap, name + ' (admin)', admin_dircap)
        collective_dircap = self.get_collective_dircap(name)
        yield self.link(rootcap, name + ' (collective)', collective_dircap)
        personal_dircap = self.get_magic_folder_dircap(name)
        yield self.link(rootcap, name + ' (personal)', personal_dircap)
        log.debug("Successfully linked folder '%s' to rootcap", name)

    @inlineCallbacks
    def unlink_magic_folder_from_rootcap(self, name):
        log.debug("Unlinking folder '%s' from rootcap...", name)
        rootcap = self.get_rootcap()
        yield self.unlink(rootcap, name + ' (collective)')
        yield self.unlink(rootcap, name + ' (personal)')
        if 'admin_dircap' in self.remote_magic_folders[name]:
            yield self.unlink(rootcap, name + ' (admin)')
        del self.remote_magic_folders[name]
        log.debug("Successfully unlinked folder '%s' from rootcap", name)

    @inlineCallbacks
    def create_magic_folder(self, path, join_code=None, admin_dircap=None,
                            poll_interval=60):  # XXX See Issue #55
        path = os.path.realpath(os.path.expanduser(path))
        poll_interval = str(poll_interval)
        try:
            os.makedirs(path)
        except OSError:
            pass
        name = os.path.basename(path)
        alias = hashlib.sha256(name.encode()).hexdigest() + ':'
        if join_code:
            yield self.command(['magic-folder', 'join', '-p', poll_interval,
                                '-n', name, join_code, path])
            if admin_dircap:
                self.add_alias(alias, admin_dircap)
        else:
            yield self.await_ready()
            yield self.command(['magic-folder', 'create', '-p', poll_interval,
                                '-n', name, alias, 'admin', path])
        self.load_magic_folders()
        yield self.link_magic_folder_to_rootcap(name)

    def local_magic_folder_exists(self, folder_name):
        if folder_name in self.magic_folders:
            return True
        return False

    def remote_magic_folder_exists(self, folder_name):
        if folder_name in self.remote_magic_folders:
            return True
        return False

    def magic_folder_exists(self, folder_name):
        if self.local_magic_folder_exists(folder_name):
            return True
        if self.remote_magic_folder_exists(folder_name):
            return True
        return False

    @inlineCallbacks
    def magic_folder_invite(self, name, nickname):
        yield self.await_ready()
        admin_dircap = self.get_admin_dircap(name)
        if not admin_dircap:
            raise TahoeError(
                'No admin dircap found for folder "{}"; you do not have the '
                'authority to create invites for this folder.'.format(name)
            )
        created = yield self.mkdir(admin_dircap, nickname)
        code = '{}+{}'.format(self.get_collective_dircap(name), created)
        return code

    @inlineCallbacks
    def magic_folder_uninvite(self, name, nickname):
        log.debug('Uninviting "%s" from "%s"...', nickname, name)
        alias = hashlib.sha256(name.encode()).hexdigest()
        yield self.unlink(self.get_alias(alias), nickname)
        log.debug('Uninvited "%s" from "%s"...', nickname, name)

    @inlineCallbacks
    def remove_magic_folder(self, name):
        if name in self.magic_folders:
            del self.magic_folders[name]
            yield self.command(['magic-folder', 'leave', '-n', name])
            self.remove_alias(hashlib.sha256(name.encode()).hexdigest())

    @inlineCallbacks
    def get_magic_folder_status(self, name):
        if not self.nodeurl or not self.api_token:
            return None
        try:
            resp = yield treq.post(
                self.nodeurl + 'magic_folder',
                {'token': self.api_token, 'name': name, 't': 'json'}
            )
        except ConnectError:
            return None
        if resp.code == 200:
            content = yield treq.content(resp)
            return json.loads(content.decode('utf-8'))
        return None

    @inlineCallbacks
    def get_json(self, cap):
        if not cap or not self.nodeurl:
            return None
        uri = '{}uri/{}/?t=json'.format(self.nodeurl, cap)
        try:
            resp = yield treq.get(uri)
        except ConnectError:
            return None
        if resp.code == 200:
            content = yield treq.content(resp)
            return json.loads(content.decode('utf-8'))
        return None

    @staticmethod
    def read_cap_from_file(filepath):
        try:
            with open(filepath) as f:
                cap = f.read().strip()
        except OSError:
            return None
        return cap

    def get_rootcap(self):
        if not self.rootcap:
            self.rootcap = self.read_cap_from_file(self.rootcap_path)
        return self.rootcap

    def get_admin_dircap(self, name):
        if name in self.magic_folders:
            try:
                return self.magic_folders[name]['admin_dircap']
            except KeyError:
                pass
        cap = self.get_alias(hashlib.sha256(name.encode()).hexdigest())
        self.magic_folders[name]['admin_dircap'] = cap
        return cap

    def _get_magic_folder_setting(self, folder_name, setting_name):
        if folder_name not in self.magic_folders:
            self.load_magic_folders()
        if folder_name in self.magic_folders:
            try:
                return self.magic_folders[folder_name][setting_name]
            except KeyError:
                return None
        return None

    def get_collective_dircap(self, name):
        return self._get_magic_folder_setting(name, 'collective_dircap')

    def get_magic_folder_dircap(self, name):
        return self._get_magic_folder_setting(name, 'upload_dircap')

    def get_magic_folder_directory(self, name):
        return self._get_magic_folder_setting(name, 'directory')

    @inlineCallbacks
    def get_magic_folders_from_rootcap(self, content=None):
        if not content:
            content = yield self.get_json(self.get_rootcap())
        if content:
            folders = defaultdict(dict)
            for name, data in content[1]['children'].items():
                data_dict = data[1]
                if name.endswith(' (collective)'):
                    prefix = name.split(' (collective)')[0]
                    folders[prefix]['collective_dircap'] = data_dict['ro_uri']
                elif name.endswith(' (personal)'):
                    prefix = name.split(' (personal)')[0]
                    folders[prefix]['upload_dircap'] = data_dict['rw_uri']
                elif name.endswith(' (admin)'):
                    prefix = name.split(' (admin)')[0]
                    folders[prefix]['admin_dircap'] = data_dict['rw_uri']
            self.remote_magic_folders = folders
            return folders
        return None

    @inlineCallbacks
    def ensure_folder_links(self, _):
        yield self.await_ready()
        if not self.get_rootcap():
            yield self.create_rootcap()
        if self.magic_folders:
            remote_folders = yield self.get_magic_folders_from_rootcap()
            for folder in self.magic_folders:
                if folder not in remote_folders:
                    self.link_magic_folder_to_rootcap(folder)
                else:
                    log.debug('Folder "%s" already linked to rootcap; '
                              'skipping.', folder)

    @inlineCallbacks
    def get_magic_folder_members(self, name, content=None):
        if not content:
            content = yield self.get_json(self.get_collective_dircap(name))
        if content:
            members = []
            children = content[1]['children']
            magic_folder_dircap = self.get_magic_folder_dircap(name)
            for member in children:
                readcap = children[member][1]['ro_uri']
                if magic_folder_dircap:
                    my_fingerprint = magic_folder_dircap.split(':')[-1]
                    fingerprint = readcap.split(':')[-1]
                    if fingerprint == my_fingerprint:
                        self.magic_folders[name]['member'] = member
                        members.insert(0, (member, readcap))
                    else:
                        members.append((member, readcap))
                else:
                    members.append((member, readcap))
            return members
        return None

    @staticmethod
    def _extract_metadata(metadata):
        try:
            deleted = metadata['metadata']['deleted']
        except KeyError:
            deleted = False
        if deleted:
            cap = metadata['metadata']['last_downloaded_uri']
        else:
            cap = metadata['ro_uri']
        return {
            'size': int(metadata['size']),
            'mtime': float(metadata['metadata']['tahoe']['linkmotime']),
            'deleted': deleted,
            'cap': cap
        }

    @inlineCallbacks
    def get_magic_folder_state(self, name, members=None):
        total_size = 0
        history_dict = {}
        if not members:
            members = yield self.get_magic_folder_members(name)
        if members:
            for member, dircap in members:
                json_data = yield self.get_json(dircap)
                try:
                    children = json_data[1]['children']
                except (TypeError, KeyError):
                    continue
                for filenode, data in children.items():
                    if filenode.endswith('@_'):
                        # Ignore subdirectories, due to Tahoe-LAFS bug #2924
                        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2924
                        continue
                    try:
                        metadata = self._extract_metadata(data[1])
                    except KeyError:
                        continue
                    metadata['path'] = filenode.replace('@_', os.path.sep)
                    metadata['member'] = member
                    history_dict[metadata['mtime']] = metadata
                    total_size += metadata['size']
        history_od = OrderedDict(sorted(history_dict.items()))
        latest_mtime = next(reversed(history_od), 0)
        return members, total_size, latest_mtime, history_od


@inlineCallbacks
def select_executable():
    if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
        # Because magic-folder on macOS has not yet landed upstream
        return os.path.join(pkgdir, 'Tahoe-LAFS', 'tahoe')
    executables = which('tahoe')
    if not executables:
        return None
    tmpdir = tempfile.TemporaryDirectory()
    tasks = []
    for executable in executables:
        log.debug(
            "Found %s; checking for multi-magic-folder support...", executable)
        tasks.append(Tahoe(tmpdir.name, executable=executable).get_features())
    results = yield DeferredList(tasks)
    for success, result in results:
        if success:
            path, has_folder_support, has_multi_folder_support = result
            if has_folder_support and has_multi_folder_support:
                log.debug("Found suitable executable: %s", path)
                return path
    return None
