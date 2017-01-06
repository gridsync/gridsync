# -*- coding: utf-8 -*-

try:
    import configparser
except ImportError:
    import ConfigParser as configparser  # pylint: disable=import-error
import datetime
import hashlib
import logging
import math
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time

import requests
from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread, blockingCallFromThread
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

from gridsync.config import Config
from gridsync.util import h2b, b2h


DEFAULT_SETTINGS = {
    "node": {
        "web.port": "tcp:0:interface=127.0.0.1"
    },
    "client": {
        "shares.happy": "1",
        "shares.total": "1",
        "shares.needed": "1"
    },
}


if getattr(sys, 'frozen', False):
    os.environ["PATH"] += os.pathsep + os.path.join(
        os.path.dirname(sys.executable), 'Tahoe-LAFS')


def decode_introducer_furl(furl):
    """Return (tub_id, connection_hints)"""
    pattern = r'^pb://([a-z2-7]+)@([a-zA-Z0-9\.:,-]+:\d+)/[a-z2-7]+$'
    match = re.match(pattern, furl.lower())
    return match.group(1), match.group(2)


class Tahoe(object):
    def __init__(self, location=None, settings=None):
        self.location = location  # introducer fURL, gateway URL, or local path
        self.settings = settings
        self.node_dir = None
        self.node_url = None
        self.status = {}
        if not location:
            pass
        elif location.startswith('pb://'):
            if not self.settings:
                self.settings = DEFAULT_SETTINGS
            self.settings['client']['introducer.furl'] = location
            _, connection_hints = decode_introducer_furl(location)
            first_hostname = connection_hints.split(',')[0].split(':')[0]
            self.node_dir = os.path.join(Config().config_dir, first_hostname)
        elif location.startswith('http://') or location.startswith('https://'):
            location += ('/' if not location.endswith('/') else '')
            self.node_url = location
        else:
            self.node_dir = os.path.join(Config().config_dir, location)
        if self.node_dir:
            self.name = os.path.basename(self.node_dir)
        else:
            self.name = location

    def get_config(self, section, option):
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        return config.get(section, option)

    def set_config(self, section, option, value):
        # XXX: This should probably preserve commented ('#'-prefixed) lines..
        logging.debug("Setting %s option %s to: %s", section, option, value)
        config = configparser.RawConfigParser(allow_no_value=True)
        config.read(os.path.join(self.node_dir, 'tahoe.cfg'))
        config.set(section, option, value)
        with open(os.path.join(self.node_dir, 'tahoe.cfg'), 'w') as f:
            config.write(f)

    def setup(self, settings):
        for section, d in settings.items():
            for option, value in d.items():
                self.set_config(section, option, value)

    def command(self, args, num_attempts=1):
        tahoe_exe = 'tahoe' + ('.exe' if sys.platform == 'win32' else '')
        if self.node_dir:
            full_args = [tahoe_exe, '-d', self.node_dir] + args
        else:
            full_args = [tahoe_exe] + args
        env = os.environ
        env['PYTHONUNBUFFERED'] = '1'
        logging.debug("Running: %s", ' '.join(full_args))
        try:
            # https://msdn.microsoft.com/en-us/library/ms684863%28v=VS.85%29.aspx
            if sys.platform == 'win32':
                proc = subprocess.Popen(
                    full_args, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True,
                    creationflags=0x08000000)
            else:
                proc = subprocess.Popen(
                    full_args, env=env, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True)
        except OSError as error:
            logging.error("Could not run tahoe executable: %s", error)
            # TODO: Notify user?
            raise
        output = ''
        for line in iter(proc.stdout.readline, ''):
            logging.debug("[pid:%s] %s", proc.pid, line.rstrip())
            output = output + line
        proc.poll()
        if proc.returncode:
            logging.error(
                "pid %s (%s) excited with code %s", proc.pid,
                ' '.join(full_args), proc.returncode)
            num_attempts -= 1
            if num_attempts:
                logging.debug(
                    "Trying again (%s attempts remaining)...", num_attempts)
                time.sleep(1)
                self.command(args, num_attempts)
            else:
                raise RuntimeError(output.rstrip())
        elif proc.returncode is None:
            logging.warning(
                "No return code for pid:%s (%s)", proc.pid,
                ' '.join(full_args))
        logging.debug(
            "pid %s (%s) excited with code %s", proc.pid, ' '.join(full_args),
            proc.returncode)
        return output.rstrip()

    def start(self):
        logging.debug("Starting Tahoe-LAFS gateway: %s", self.location)
        if not self.node_dir:
            logging.debug(
                "Tahoe-LAFS gateway %s running remotely; no need to start",
                self.node_url)
            return
        elif not os.path.isdir(self.node_dir):
            logging.debug(
                "%s not found; creating node dir...", self.node_dir)
            self.command(['create-client'])
        elif not os.path.isfile(os.path.join(self.node_dir, 'tahoe.cfg')):
            logging.debug(
                "%s found but tahoe.cfg is missing; creating node dir...",
                self.node_dir)
            self.command(['create-client'])
        if self.settings:
            self.setup(self.settings)
        if not os.path.isfile(os.path.join(self.node_dir, 'twistd.pid')):
            self.command(['start'])
        else:
            pid = int(open(os.path.join(self.node_dir, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command(['start'])
        self.node_url = open(
            os.path.join(self.node_dir, 'node.url')).read().strip()
        logging.debug("Node URL is: %s", self.node_url)

    def mkdir(self):
        # TODO: Allow subdirs?
        url = self.node_url + 'uri?t=mkdir'
        r = requests.post(url)
        r.raise_for_status()
        return r.content.decode()

    def ls(self, dircap):
        url = self.node_url + 'uri/' + dircap + '?t=json'
        r = requests.get(url)
        r.raise_for_status()
        items = [item for item in r.json()[1]['children'].keys()]
        return sorted(items)

    def get_info(self, cap):
        url = self.node_url + 'uri/' + cap + '?t=json'
        r = requests.get(url)
        r.raise_for_status()
        return r.json()

    def get_operations(self):
        url = self.node_url + 'status?t=json'
        r = requests.get(url)
        r.raise_for_status()
        return r.json()['active']

    def get_sharemap(self, storage_index):
        url = self.node_url + 'status/'
        r = requests.get(url)
        r.raise_for_status()
        html = r.text
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if storage_index in line:
                operation_url = url + lines[i + 4].split('"')[1]
                break
        r = requests.get(operation_url)
        r.raise_for_status()
        html = r.text
        lines = html.split('\n')
        sharemap = {}
        for line in lines:
            if "Sharemap:" in line:
                mappings = line.split('<li>')[2:]
                for mapping in mappings:
                    share = mapping.split('-&gt;')[0]
                    server = mapping.split('[')[1].split(']')[0]
                    sharemap[share] = server
                return sharemap

    def update_status(self):
        # https://tahoe-lafs.org/trac/tahoe-lafs/ticket/2476
        html = requests.get(self.node_url).text
        p = re.compile("Connected to <span>(.+?)</span>")
        self.status['servers_connected'] = int(re.findall(p, html)[0])
        p = re.compile("of <span>(.+?)</span> known storage servers")
        self.status['servers_known'] = int(re.findall(p, html)[0])

        servers = {}
        p = re.compile('<div class="nodeid">(.+?)</div>')
        nodeid = re.findall(p, html)
        for item in nodeid:
            servers[item] = {}

        def insert_all(s, tag='td'):
            p = re.compile('<{} class="{}">(.+?)</{}>'.format(tag, s, tag))
            for index, item in enumerate(re.findall(p, html)):
                key = s.replace('service-', '').replace('-', '_').replace(' ', '_')
                servers[nodeid[index]][key] = item

        insert_all('nickname', 'div')
        insert_all('address')
        insert_all('service-service-name')
        insert_all('service-since timestamp')
        insert_all('service-announced timestamp')
        insert_all('service-version')
        insert_all('service-available-space')

        p = re.compile('<div class="furl">(.+?)</div>')
        r = re.findall(p, html)
        self.status['introducer'] = {'furl': r[0]}
        self.status['helper'] = {'furl': r[1]}
        self.status['servers'] = servers

        p = re.compile('<div class="status-indicator">(.+?)</div>')
        l = re.findall(p, html)
        for index, item in enumerate(l):
            p = re.compile('alt="(.+?)"')
            status = re.findall(p, item)[0]
            if index == 0:
                self.status['introducer']['status'] = status
            elif index == 1:
                self.status['helper']['status'] = status
            else:
                self.status['servers'][nodeid[index - 2]]['status'] = status
        total_available_space = 0
        for _, v in self.status['servers'].items():
            try:
                total_available_space += h2b(v['available_space'])
            except ValueError:
                pass
        self.status['total_available_space'] = b2h(total_available_space)

    def adjust(self):
        """Adjust erasure coding paramaters to Sensible(tm) values

        'Sensible' here is determined in accordance with the number of
        available storage nodes, where N = the total number of currently
        available nodes, K = (N * 0.3), and H = (N * 0.7).

        Adjusting these values is followed by restarting the running node.
        """
        logging.debug("Adjusting erasure coding parameters...")
        shares_total = int(self.status.get('servers_connected', 1))  # N
        shares_needed = int(math.ceil(shares_total * 0.3))  # K
        shares_happy = int(math.ceil(shares_total * 0.7))  # H
        self.set_config('client', 'shares.total', shares_total)
        self.set_config('client', 'shares.needed', shares_needed)
        self.set_config('client', 'shares.happy', shares_happy)
        self.command(['stop'])
        self.start()

    def stored(self, filepath, size=None, mtime=None):
        """Return filecap if filepath has been stored previously via backup"""
        if not size:
            try:
                size = os.path.getsize(filepath)
            except OSError:
                return
        if not mtime:
            try:
                mtime = int(os.path.getmtime(filepath))
            except OSError:
                return
        db = os.path.join(self.node_dir, 'private', 'backupdb.sqlite')
        if not os.path.isfile(db):
            return
        connection = sqlite3.connect(db)
        with connection:
            try:
                cursor = connection.cursor()
                cursor.execute(
                    'SELECT "filecap" FROM "caps" WHERE fileid=('
                    'SELECT "fileid" FROM "local_files" WHERE path=? '
                    'AND size=? AND mtime=?)', (filepath, size, mtime))
                return cursor.fetchone()[0]
            except TypeError:
                return

    def get_aliases(self):
        aliases = {}
        aliases_file = os.path.join(self.node_dir, 'private', 'aliases')
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

    def get_dircap_from_alias(self, alias):
        if not alias.endswith(':'):
            alias = alias + ':'
        try:
            for name, cap in self.get_aliases().items():
                if name == alias:
                    return cap
        except AttributeError:
            return

    def get_alias_from_dircap(self, dircap):
        try:
            for name, cap in self.get_aliases().items():
                if cap == dircap:
                    return name
        except AttributeError:
            return

    def aliasify(self, dircap_or_alias):
        """Return a valid alias corresponding to a given dircap or alias.

        Return the alias of the given dircap, if it already exists, or, if
        it doesn't, add and return an alias using the SHA-256 hash of the
        dircap as the name.

        If an alias is passed instead of a dircap, return it only if it
        corresponds to a valid dircap, raising a ValueError if the dircap
        is invalid, or a LookupError if it is missing from the aliases file.
        """
        if dircap_or_alias.startswith('URI:DIR'):
            alias = self.get_alias_from_dircap(dircap_or_alias)
            if alias:
                return alias
            else:
                hash_of_dircap = hashlib.sha256(
                    dircap_or_alias.encode('utf-8')).hexdigest()
                self.command(['add-alias', hash_of_dircap, dircap_or_alias])
                return self.get_alias_from_dircap(dircap_or_alias)
        else:
            dircap = self.get_dircap_from_alias(dircap_or_alias)
            if dircap:
                if dircap.startswith('URI:DIR'):
                    return dircap_or_alias
                else:
                    raise ValueError('Invalid alias for {} ({})'.format(
                        dircap_or_alias, dircap))
            #else:
            #    self.command(['create-alias', dircap_or_alias])
            #    return dircap_or_alias
            else:
                raise LookupError('No dircap found for alias {}'.format(
                    dircap_or_alias))


class SyncFolder(PatternMatchingEventHandler):
    def __init__(self, parent, local_dir, remote_dircap, tahoe=None,  # pylint: disable=too-many-arguments
                 ignore_patterns=None):
        self.parent = parent
        _ignore_patterns = ['*.gridsync-versions*', '*.part*',
                            '*(conflicted copy *-*-* *-*-*)*']
        if ignore_patterns:
            _ignore_patterns += ignore_patterns
        super(SyncFolder, self).__init__(ignore_patterns=_ignore_patterns)
        if not tahoe:
            tahoe = Tahoe()
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        self.remote_dircap_alias = None
        self.versions_dir = os.path.join(self.local_dir, '.gridsync-versions')
        self.local_snapshot = 0
        self.filesystem_modified = False
        self.do_backup = False
        self.do_sync = False
        self.sync_state = 0
        self.sync_log = []
        self.keep_versions = 1
        self.local_checker = LoopingCall(self.check_for_changes)
        self.remote_checker = LoopingCall(reactor.callInThread, self.sync)
        self.observer = None
        logging.debug("%s initialized; %s <-> %s", self, self.local_dir,
                      self.remote_dircap)

    def on_modified(self, event):
        self.filesystem_modified = True
        #try:
        #    reactor.callFromThread(self.local_checker.start, 1)
        #except AssertionError:
        #    return
        reactor.callFromThread(self._start_local_checker)

    def _start_local_checker(self):
        # XXX: For some (qt5reactor-related?) reason, the AssertionError
        # raised by trying to start the (already-running) local_checker timer
        # above won't catch if called from reactor.callFromThread. Why is this?
        try:
            self.local_checker.start(1)
        except AssertionError:
            return

    def check_for_changes(self):
        if self.filesystem_modified:
            self.filesystem_modified = False
        else:
            reactor.callFromThread(self.local_checker.stop)
            reactor.callInThread(self.sync, force_backup=True)

    def start(self):
        try:
            self.remote_dircap_alias = self.tahoe.aliasify(self.remote_dircap)
        except ValueError:
            # TODO: Alert user alias is garbled?
            pass
        except LookupError:
            # TODO: Alert user alias is missing?
            pass
        logging.info("Starting Observer in %s...", self.local_dir)
        self.observer = Observer()
        self.observer.schedule(self, self.local_dir, recursive=True)
        self.observer.start()
        reactor.callFromThread(self.remote_checker.start, 30)

    def _create_conflicted_copy(self, filepath):  # pylint: disable=no-self-use
        base, extension = os.path.splitext(filepath)
        mtime = int(os.path.getmtime(filepath))
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
        tagged_filepath = base + tag + extension
        logging.debug(
            "Creating conflicted copy of %s %s", filepath, tagged_filepath)
        os.rename(filepath, tagged_filepath)
        os.utime(tagged_filepath, (-1, mtime))

    def _create_versioned_copy(self, filename, mtime):
        local_filepath = os.path.join(self.local_dir, filename)
        base, extension = os.path.splitext(filename)
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(%Y-%m-%d %H-%M-%S)')
        newname = base + tag + extension
        versioned_filepath = newname.replace(self.local_dir, self.versions_dir)
        if not os.path.isdir(os.path.dirname(versioned_filepath)):
            os.makedirs(os.path.dirname(versioned_filepath))
        logging.info("Creating %s", versioned_filepath)
        shutil.copy2(local_filepath, versioned_filepath)

    def get_local_metadata(self, basedir=None):
        metadata = {}
        if not basedir:
            basedir = self.local_dir
        for root, dirs, files in os.walk(basedir, followlinks=True):
            for name in dirs:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {}
            for name in files:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {
                        'mtime': int(os.path.getmtime(path)),
                        'size': os.path.getsize(path)}
        return metadata

    def get_remote_metadata(self, dircap, basedir=''):
        metadata = {}
        jobs = []
        logging.debug("Getting remote metadata from %s...", dircap)
        url = '{}uri/{}/?t=json'.format(self.tahoe.node_url, dircap)
        received_data = requests.get(url).json()
        for filename, data in received_data[1]['children'].items():
            path = '/'.join([basedir, filename]).strip('/')
            metadata[path] = {
                'uri': data[1]['ro_uri'],
                'mtime': int(data[1]['metadata']['mtime'])}
            if data[0] == 'dirnode':
                jobs.append(
                    deferToThread(self.get_remote_metadata,
                                  '/'.join([dircap, filename]), path))
        results = blockingCallFromThread(reactor, gatherResults, jobs)
        for result in results:
            metadata.update(result)
        return metadata

    def sync(self, snapshot=None, force_backup=False): # flake8: noqa
        # FIXME ...
        if self.sync_state:
            logging.debug("Sync already in progress; queueing to end...")
            self.do_sync = True
            return
        if not snapshot:
            try:
                ls = self.tahoe.ls(self.remote_dircap)
                if not ls:
                    logging.debug("No /Archives found; "
                                  "performing (first?) backup...")
                    self.sync_state += 1
                    self.backup(self.local_dir, self.remote_dircap_alias)
                    self.sync_complete(ls)
                    return
            except Exception as error:
                logging.error(error)
                return
            # XXX: It might be preferable to just check the dircap of /Latest/
            pre_sync_archives = self.tahoe.ls(self.remote_dircap + "/Archives")
            available_snapshot = pre_sync_archives[-1]
            if self.local_snapshot == available_snapshot:
                if force_backup:
                    self.sync_state += 1
                    self.backup(self.local_dir, self.remote_dircap_alias)
                    self.sync_complete(pre_sync_archives)
                return
            else:
                snapshot = available_snapshot
        remote_path = self.remote_dircap + '/Archives/' + snapshot
        logging.info("Syncing %s with %s...", self.local_dir, snapshot)
        self.sync_state += 1
        local_metadata = self.get_local_metadata(self.local_dir)
        remote_metadata = self.get_remote_metadata(remote_path)
        # TODO: If tahoe.get_metadata() fails or doesn't contain a
        # valid snapshot, jump to backup?
        jobs = []
        for file, metadata in remote_metadata.items():
            if metadata['uri'].startswith('URI:DIR'):
                dirpath = os.path.join(self.local_dir, file)
                if not os.path.isdir(dirpath):
                    logging.info("Creating directory: %s...", dirpath)
                    os.makedirs(dirpath)
        for file, metadata in remote_metadata.items():
            if not metadata['uri'].startswith('URI:DIR'):
                filepath = os.path.join(self.local_dir, file)
                remote_mtime = metadata['mtime']
                if filepath in local_metadata:
                    #local_filesize = local_metadata[filepath]['size']
                    local_mtime = local_metadata[filepath]['mtime']
                    if local_mtime < remote_mtime:
                        logging.debug(
                            "[<] %s is older than remote version; "
                            "downloading %s...", file, file)
                        if self.keep_versions:
                            self._create_versioned_copy(filepath, local_mtime)
                        jobs.append(
                            deferToThread(
                                self.download, remote_path + '/' + file,
                                filepath, remote_mtime))
                    elif local_mtime > remote_mtime:
                        logging.debug(
                            "[>] %s is newer than remote version; "
                            "backup scheduled", file)
                        self.do_backup = True
                    else:
                        logging.debug("[.] %s is up to date.", file)
                else:
                    logging.debug(
                        "[?] %s is missing; downloading %s...", file, file)
                    jobs.append(
                        deferToThread(
                            self.download, remote_path + '/' + file,
                            filepath, remote_mtime))
        for file, metadata in local_metadata.items():
            fn = file.split(self.local_dir + os.path.sep)[1]
            if fn not in remote_metadata:
                if metadata:
                    recovery_uri = self.tahoe.stored(
                        file, metadata['size'], metadata['mtime'])
                    if recovery_uri:
                        logging.debug(
                            "[x] %s removed from latest snapshot; "
                            "deleting local file...", file)
                        if self.keep_versions:
                            self._create_versioned_copy(file, local_mtime)
                        try:
                            os.remove(file)
                        except Exception as error:
                            logging.error(error)
                    else:
                        logging.debug(
                            "[!] %s isn't stored; backup scheduled", fn)
                        self.do_backup = True
        blockingCallFromThread(reactor, gatherResults, jobs)
        if self.do_backup:
            self.backup(self.local_dir, self.remote_dircap_alias)
            self.do_backup = False
        if self.do_sync:
            self.sync()
        self.sync_complete(pre_sync_archives)

    def sync_complete(self, pre_sync_archives):
        post_sync_archives = self.tahoe.ls(self.remote_dircap + "/Archives")
        if len(post_sync_archives) - len(pre_sync_archives) <= 1:
            self.local_snapshot = post_sync_archives[-1]
            logging.info(
                "Synchronized %s with %s",
                self.local_dir,
                self.local_snapshot)
        else:
            logging.warning("Remote state changed during sync")
            # TODO: Re-sync/merge overlooked snapshot
        self.sync_state -= 1

    def download(self, remote_uri, local_filepath, mtime=None):
        url = self.tahoe.node_url + 'uri/' + remote_uri
        download_path = local_filepath + '.part'
        # XXX: Resuming may not be a good idea, as the existent (local)
        # parts may no longer be present in the latest (remote) version of
        # the file. Perhaps an integrity/filecap check should be required?
        #if os.path.exists(download_path):
        #    size = os.path.getsize(download_path)
        #    logging.debug("Partial download of {} found; resuming byte {}..."\
        #            .format(local_filepath, size))
        #    request.headers['Range'] = 'bytes={}-'.format(size)
        # TODO: Handle exceptions..
        if os.path.isfile(download_path) or os.path.isdir(download_path):
            raise OSError("File exists: '{}'".format(download_path))
        r = requests.get(url, stream=True)
        r.raise_for_status()
        recv = 0
        with open(download_path, 'wb') as f:
            for chunk in r.iter_content(4096):
                f.write(chunk)
                recv += len(chunk)
        if os.path.isfile(local_filepath):
            local_filesize = os.path.getsize(local_filepath)
            if not self.tahoe.stored(local_filepath, local_filesize, mtime):
                self._create_conflicted_copy(local_filepath)
        os.rename(download_path, local_filepath)
        if mtime:
            os.utime(local_filepath, (-1, mtime))
        self.sync_log.append("Downloaded {}".format(
            local_filepath.lstrip(self.local_dir)))
        return recv

    def backup(self, local_dir, remote_dircap):
        excludes = ['--exclude=' + x for x in self.ignore_patterns]
        output = self.tahoe.command(
            ['backup', '-v'] + excludes + [local_dir, remote_dircap])
        files_added = ''
        for line in output.split('\n'):
            if line.startswith('uploading'):
                filename = os.path.basename(line[11:][:-3])
                #self.sync_log.append("Uploaded {}".format(filename))
                if not files_added:
                    files_added += "Uploaded " + filename
                else:
                    files_added += ',' + filename
        reactor.callFromThread(
            self.parent.notify, "Sync complete", files_added)

    def stop(self):
        logging.info("Stopping Observer in %s...", self.local_dir)
        self.observer.stop()
        self.observer.join()
        self.remote_checker.stop()
