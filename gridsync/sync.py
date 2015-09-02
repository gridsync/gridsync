# -*- coding: utf-8 -*-

import datetime
import hashlib
import logging
import os
import shutil
import time

from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.threads import deferToThread, blockingCallFromThread

from gridsync.watcher import LocalWatcher, RemoteWatcher


class SyncFolder():
    def __init__(self, local_dir, remote_dircap, tahoe=None):
        if not tahoe:
            from gridsync.tahoe import Tahoe
            tahoe = Tahoe()
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        self.versions_dir = os.path.join(self.local_dir, '.gridsync-versions')
        self.local_snapshot = 0
        self.do_backup = False
        self.sync_state = 0
        self.sync_log = []
        logging.debug("{} initialized; "
                "{} <-> {}".format(self, self.local_dir, self.remote_dircap))

    def start(self):
        alias = hashlib.sha256(self.remote_dircap).hexdigest()
        self.tahoe.command(['add-alias', alias, self.remote_dircap])
        self.remote_dircap = alias + ":"
        self.local_watcher = LocalWatcher(self, self.local_dir)
        self.remote_watcher = RemoteWatcher(self, self.remote_dircap, self.tahoe)
        self.local_watcher.start()
        self.remote_watcher.start()

    def _create_conflicted_copy(self, filename, mtime):
        base, extension = os.path.splitext(filename)
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
        newname = base + tag + extension
        shutil.copy2(filename, newname)

    def _create_versioned_copy(self, filename, mtime):
        local_filepath = os.path.join(self.local_dir, filename)
        base, extension = os.path.splitext(filename)
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(%Y-%m-%d %H-%M-%S)')
        newname = base + tag + extension
        versioned_filepath = os.path.join(self.versions_dir, newname)
        if not os.path.isdir(os.path.dirname(versioned_filepath)):
            os.makedirs(os.path.dirname(versioned_filepath))
        logging.info("Creating {}".format(versioned_filepath))
        shutil.copy2(local_filepath, versioned_filepath)

    def sync(self, snapshot=None):
        # TODO: Prevent from running and/or queue to end if already sync_state
        if not snapshot:
            available_snapshot = self.remote_watcher.get_latest_snapshot()
            if self.local_snapshot == available_snapshot:
                self.sync_state += 1
                self.backup(self.local_dir, self.remote_dircap)
                self.sync_complete()
                return
            else:
                snapshot = available_snapshot
        remote_path = self.remote_dircap + 'Archives/' + snapshot
        logging.info("Syncing {} with {}...".format(self.local_dir, snapshot))
        self.sync_state += 1
        self.local_metadata = self.local_watcher.get_metadata(self.local_dir)
        self.remote_metadata = self.remote_watcher.get_metadata(remote_path)
        # TODO: If tahoe.get_metadata() fails or doesn't contain a
        # valid snapshot, jump to backup?
        jobs = []
        for file, metadata in self.remote_metadata.iteritems():
            if metadata['uri'].startswith('URI:DIR'):
                dirpath = os.path.join(self.local_dir, file)
                if not os.path.isdir(dirpath):
                    logging.info("Creating directory: {}...".format(dirpath))
                    os.makedirs(dirpath)
        for file, metadata in self.remote_metadata.iteritems():
            if not metadata['uri'].startswith('URI:DIR'):
                filepath = os.path.join(self.local_dir, file)
                remote_mtime = int(metadata['mtime'])
                if filepath in self.local_metadata:
                    local_mtime = int(self.local_metadata[filepath]['mtime'])
                    if local_mtime < remote_mtime:
                        logging.debug("[<] {} is older than remote version; "
                                "downloading {}...".format(file, file))
                        self._create_versioned_copy(filepath, local_mtime)
                        jobs.append(deferToThread(self.download,
                            remote_path + '/' + file, filepath, remote_mtime))
                    elif local_mtime > remote_mtime:
                        logging.debug("[>] {} is newer than remote version; "
                                "backup scheduled".format(file)) 
                        self.do_backup = True
                    else:
                        logging.debug("[.] {} is up to date.".format(file))
                else:
                    logging.debug("[?] {} is missing; "
                            "downloading {}...".format(file, file))
                    jobs.append(deferToThread(self.download,
                        remote_path + '/' + file, filepath, remote_mtime))
        for file, metadata in self.local_metadata.iteritems():
            fn = file.split(self.local_dir + os.path.sep)[1]
            if fn not in self.remote_metadata:
                # TODO: Distinguish between local files that haven't
                # been stored and intentional (remote) deletions
                # (perhaps only polled syncs should delete?)
                logging.debug("[!] {} isn't stored; "
                        "backup scheduled".format(file))
                self.do_backup = True
        blockingCallFromThread(reactor, gatherResults, jobs)
        if self.do_backup:
            self.backup(self.local_dir, self.remote_dircap)
            self.do_backup = False
        self.sync_complete()

    def sync_complete(self):
        self.local_snapshot = self.remote_watcher.get_latest_snapshot() # XXX Race
        logging.info("Synchronized {} with {}".format(
                self.local_dir, self.local_snapshot))
        self.sync_state -= 1

    def download(self, remote_uri, local_filepath, mtime=None):
        self.tahoe.command(['get', remote_uri, local_filepath])
        if mtime:
            os.utime(local_filepath, (-1, mtime))
        self.sync_log.append("Downloaded {}".format(
            local_filepath.lstrip(self.local_dir)))

    def backup(self, local_dir, remote_dircap):
        output = self.tahoe.command(['backup', '-v', 
            '--exclude=*.gridsync-versions*', local_dir, remote_dircap])
        for line in output.split('\n'):
            if line.startswith('uploading'):
                filename = line.split()[1][:-3][1:].lstrip(self.local_dir) # :/
                self.sync_log.append("Uploaded {}".format(filename))

    def stop(self):
        self.local_watcher.stop()
        self.remote_watcher.stop()

