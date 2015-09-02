# -*- coding: utf-8 -*-

import logging
import os
import time

from twisted.internet import reactor
from twisted.internet.defer import gatherResults
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread, blockingCallFromThread
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer


class LocalWatcher(PatternMatchingEventHandler):
    def __init__(self, parent, local_dir):
        super(LocalWatcher, self).__init__(
                ignore_patterns=["*.gridsync-versions*"])
        self.parent = parent
        self.local_dir = os.path.expanduser(local_dir)
        self.versions_dir = os.path.join(self.local_dir, '.gridsync-versions')
        self.filesystem_modified = False
        logging.debug("LocalWatcher initialized for {} ({})".format(
                self.local_dir, self))
        self.local_checker = LoopingCall(self.check_for_changes)

    def start(self):
        logging.info("Starting Observer in {}...".format(self.local_dir))
        try:
            self.observer = Observer()
            self.observer.schedule(self, self.local_dir, recursive=True)
            self.observer.start()
        except Exception, e:
            logging.error(e)

    def on_modified(self, event):
        self.filesystem_modified = True
        try:
            self.local_checker.start(1)
        except:
            return

    def check_for_changes(self):
        if self.filesystem_modified:
            self.filesystem_modified = False
        else:
            try:
                self.local_checker.stop()
                if not self.parent.sync_state:
                    reactor.callInThread(self.parent.sync)
                else:
                    # XXX Useful only if sync() isn't in backup phase; fix
                    self.parent.do_backup = True
            except:
                return

    def get_metadata(self, basedir=None):
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
                        'mtime': os.path.getmtime(path),
                        'size': os.path.getsize(path)
                    }
        return metadata

    def stop(self):
        logging.info("Stopping Observer in {}...".format(self.local_dir))
        try:
            self.observer.stop()
            self.observer.join()
        except Exception, e:
            logging.error(e)


class RemoteWatcher():
    def __init__(self, parent, remote_dircap, tahoe=None):
        if not tahoe:
            from gridsync.tahoe import Tahoe
            tahoe = Tahoe()
        self.parent = parent
        self.tahoe = tahoe
        self.remote_dircap = remote_dircap
        logging.debug("RemoteWatcher initialized for {} ({})".format(
                self.remote_dircap, self))

    def start(self):
        self.remote_checker = LoopingCall(reactor.callInThread, 
                self.check_for_changes)
        self.remote_checker.start(30)

    def check_for_changes(self, num_attempts=3):
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
                self.check_for_changes(num_attempts - 1)
            else:
                logging.debug("Attempts exhausted; attempting repair...")
                # XXX
            return
        if remote_snapshot != self.parent.local_snapshot:
            logging.debug("New snapshot available: {}".format(remote_snapshot))
            if not self.parent.sync_state:
                #reactor.callInThread(self.parent.sync, snapshot=remote_snapshot)
                self.parent.sync(snapshot=remote_snapshot)

    def get_latest_snapshot(self):
        # TODO: If /Archives doesn't exist, perform (first?) backup?
        dircap = self.remote_dircap + "Archives"
        j = self.tahoe.ls_json(dircap)
        snapshots = []
        for snapshot in j[1]['children']:
            snapshots.append(snapshot)
        snapshots.sort()
        return snapshots[-1:][0]

    def get_metadata(self, dircap, basedir=''):
        # TODO: If /Archives doesn't exist, perform (first?) backup?
        metadata = {}
        received_data = self.tahoe.ls_json(dircap)
        logging.debug("Getting remote metadata from {}...".format(dircap))
        jobs = []
        for filename, data in received_data[1]['children'].iteritems():
            path = '/'.join([basedir, filename]).strip('/')
            metadata[path] = {
                'uri': data[1]['ro_uri'],
                'mtime': data[1]['metadata']['mtime'],
            }
            if data[0] == 'dirnode':
                jobs.append(deferToThread(self.get_metadata,
                    metadata[path]['uri'], path))
        results = blockingCallFromThread(reactor, gatherResults, jobs)
        for result in results:
            metadata.update(result)
        return metadata

    def stop(self):
        self.remote_checker.stop()

