# -*- coding: utf-8 -*-

import json
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
                        'mtime': int(os.path.getmtime(path)),
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
        self.link_time = 0
        logging.debug("RemoteWatcher initialized for {} ({})".format(
                self.remote_dircap, self))

    def start(self):
        self.remote_checker = LoopingCall(reactor.callInThread, 
                self.check_for_changes)
        self.remote_checker.start(30)

    def check_for_changes(self):
        logging.debug("Checking for new snapshot...")
        try:
            received_data = json.loads(self.tahoe.command(['ls', '--json',
                self.remote_dircap], debug_output=False, num_attempts=5))
        except RuntimeError, error:
            logging.error(error)
            # TODO: Auto-repair
            return
        metadata = received_data[1]['children']['Latest'][1]['metadata']
        latest_link_time = metadata['tahoe']['linkmotime']
        if latest_link_time > self.link_time:
            logging.debug("New snapshot available ({}); syncing...".format(
                metadata['tahoe']['linkmotime']))
            if not self.parent.sync_state:
                self.parent.sync()
                self.link_time = latest_link_time
            else:
                # TODO: Insert (re)sync flag
                pass

    def get_latest_snapshot(self):
        # TODO: If /Archives doesn't exist, perform (first?) backup?
        dircap = self.remote_dircap + "Archives"
        j = json.loads(self.tahoe.command(['ls', '--json', dircap],
            debug_output=False))
        snapshots = []
        for snapshot in j[1]['children']:
            snapshots.append(snapshot)
        snapshots.sort()
        return snapshots[-1:][0]

    def get_metadata(self, dircap, basedir=''):
        # TODO: If /Archives doesn't exist, perform (first?) backup?
        metadata = {}
        jobs = []
        logging.debug("Getting remote metadata from {}...".format(dircap))
        received_data = json.loads(self.tahoe.command(['ls', '--json', dircap],
                debug_output=False))
        for filename, data in received_data[1]['children'].iteritems():
            path = '/'.join([basedir, filename]).strip('/')
            metadata[path] = {
                'uri': data[1]['ro_uri'],
                'mtime': int(data[1]['metadata']['mtime']),
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

