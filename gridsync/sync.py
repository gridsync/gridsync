# -*- coding: utf-8 -*-

import datetime
import logging
import os
import shutil
import time

from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread, blockingCallFromThread
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class SyncFolder(PatternMatchingEventHandler):
    def __init__(self, local_dir, remote_dircap, tahoe=None):
        super(SyncFolder, self).__init__(
                ignore_patterns=["*.gridsync-versions*"])
        if not tahoe:
            from gridsync.tahoe import Tahoe
            tahoe = Tahoe()
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        self.versions_dir = os.path.join(self.local_dir, '.gridsync-versions')
        self.local_snapshot = 0
        self.filesystem_modified = False
        self.do_backup = False
        self.sync_state = 0
        self.sync_log = []
        logging.debug("{} initialized; "
                "{} <-> {}".format(self, self.local_dir, self.remote_dircap))

    def start(self):
        self.local_checker = LoopingCall(self.check_for_backup)
        self.local_checker.start(1)
        self.remote_checker = LoopingCall(
                reactor.callInThread, self.check_for_new_snapshot)
        self.remote_checker.start(30)
        self.start_observer()

    def on_modified(self, event):
        self.filesystem_modified = True

    def check_for_backup(self):
        if self.filesystem_modified:
            self.filesystem_modified = False
            if self.sync_state:
                #self.do_backup = True
                pass
            else:
                reactor.callInThread(self.wait_for_writes)

    def wait_for_writes(self):
        time.sleep(1)
        if not self.filesystem_modified:
            self.perform_backup()

    def perform_backup(self):
        remote_snapshot = self.get_latest_snapshot()
        if self.local_snapshot == remote_snapshot:
            self.sync(skip_comparison=True)
        else:
            self.sync(snapshot=remote_snapshot)

    def check_for_new_snapshot(self, num_attempts=3):
        logging.debug("Checking for new snapshot...")
        try:
            remote_snapshot = self.get_latest_snapshot()
        except Exception, e:
            logging.error(e)
            if num_attempts:
                logging.debug("get_latest_snapshot() failed; "
                        "(maybe we're not connected yet?).")
                logging.debug("Trying again after 1 sec. "
                        "({} attempts remaining)...".format(num_attempts))
                time.sleep(1)
                self.check_for_new_snapshot(num_attempts - 1)
            else:
                logging.debug("Attempts exhausted; attempting repair...")
                # XXX
            return
        if remote_snapshot != self.local_snapshot:
            logging.debug("New snapshot available: {}".format(remote_snapshot))
            if not self.sync_state:
                #reactor.callInThread(self.sync, snapshot=remote_snapshot)
                self.sync(snapshot=remote_snapshot)

    def get_latest_snapshot(self):
        # TODO: If /Archives doesn't exist, perform (first?) backup?
        dircap = self.remote_dircap + "/Archives"
        j = self.tahoe.ls_json(dircap)
        snapshots = []
        for snapshot in j[1]['children']:
            snapshots.append(snapshot)
        snapshots.sort()
        return snapshots[-1:][0]

    def get_local_metadata(self, basedir):
        metadata = {}
        for root, dirs, files in os.walk(basedir, followlinks=True):
            for name in dirs:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {}
            for name in files:
                path = os.path.join(root, name)
                if not path.startswith(self.versions_dir):
                    metadata[path] = {
                        'mtime': os.path.getmtime(path),
                        'size': os.path.getsize(path)
                    }
        return metadata

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

    def get_remote_metadata(self, dircap, basedir=''):
        metadata = {}
        logging.debug("Getting remote metadata from {}...".format(dircap))
        received_data = self.tahoe.ls_json(dircap)
        jobs = []
        for filename, data in received_data[1]['children'].iteritems():
            path = '/'.join([basedir, filename]).strip('/')
            metadata[path] = {
                'uri': data[1]['ro_uri'],
                'mtime': data[1]['metadata']['mtime'],
            }
            if data[0] == 'dirnode':
                jobs.append(deferToThread(self.get_remote_metadata, 
                    metadata[path]['uri'], path))
        results = blockingCallFromThread(reactor, gatherResults, jobs)
        for result in results:
            metadata.update(result)
        return metadata

    def sync(self, snapshot='Latest', skip_comparison=False):
        if snapshot != 'Latest':
            snapshot = 'Archives/' + snapshot
        self.sync_state += 1
        logging.info("Syncing {} with {}...".format(self.local_dir, snapshot))
        if skip_comparison:
            self.backup(self.local_dir, self.remote_dircap)
            self.sync_complete()
            return
        remote_path = '/'.join([self.remote_dircap, snapshot])
        self.local_metadata = self.get_local_metadata(self.local_dir)
        self.remote_metadata = self.get_remote_metadata(remote_path)
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
                    #if remote_mtime > local_mtime: # Remote is newer; download
                    if local_mtime < remote_mtime: # Remote is newer; download
                        logging.debug("[<] {} is older than remote version; "
                                "downloading {}...".format(file, file))
                        self._create_versioned_copy(filepath, local_mtime)
                        jobs.append(deferToThread(self.download,
                            metadata['uri'], filepath, remote_mtime))
                    #elif remote_mtime < local_mtime: # Local is newer; backup
                    elif local_mtime > remote_mtime: # Local is newer; backup
                        logging.debug("[>] {} is newer than remote version; "
                                "backup scheduled".format(file)) 
                        self.do_backup = True
                    else:
                        logging.debug("[.] {} is up to date.".format(file))
                else:
                    logging.debug("[?] {} is missing; "
                            "downloading {}...".format(file, file))
                    jobs.append(deferToThread(self.download,
                        metadata['uri'], filepath, remote_mtime))
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
        self.local_snapshot = self.get_latest_snapshot() # XXX Race
        logging.info("Synchronized {} with {}".format(
                self.local_dir, self.local_snapshot))
        self.sync_state -= 1

    def download(self, remote_uri, local_filepath, mtime=None):
        self.tahoe.get(remote_uri, local_filepath)
        if mtime:
            os.utime(local_filepath, (-1, mtime))
        self.sync_log.append("Downloaded {}".format(
            local_filepath.lstrip(self.local_dir)))

    def backup(self, local_dir, remote_uri):
        output = self.tahoe.backup(self.local_dir, self.remote_dircap)
        for line in output.split('\n'):
            if line.startswith('uploading'):
                filename = line.split()[1][:-3][1:].lstrip(self.local_dir) # :/
                self.sync_log.append("Uploaded {}".format(filename))

    def start_observer(self):
        logging.info("Starting Observer in {}...".format(self.local_dir))
        try:
            self.observer = Observer()
            self.observer.schedule(self, self.local_dir, recursive=True)
            self.observer.start()
        except Exception, e:
            logging.error(e)

    def stop_observer(self):
        logging.info("Stopping Observer in {}...".format(self.local_dir))
        try:
            self.observer.stop()
            self.observer.join()
        except Exception, e:
            logging.error(e)

    def stop(self):
        logging.info("Stopping SyncFolder ({} <-> {})"
                .format(self.local_dir, self.remote_dircap))
        self.local_checker.stop()
        self.remote_checker.stop()
        self.stop_observer()

