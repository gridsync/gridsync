# -*- coding: utf-8 -*-

import logging
import os

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
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
        except Exception, error:
            logging.error(error)

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
                reactor.callInThread(self.parent.sync)
            except:
                return

    def stop(self):
        logging.info("Stopping Observer in {}...".format(self.local_dir))
        try:
            self.observer.stop()
            self.observer.join()
        except Exception, error:
            logging.error(error)


class RemoteWatcher():
    def __init__(self, parent, remote_dircap, tahoe):
        self.parent = parent
        self.tahoe = tahoe
        self.remote_dircap = remote_dircap
        logging.debug("RemoteWatcher initialized for {} ({})".format(
                self.remote_dircap, self))

    def start(self):
        self.remote_checker = LoopingCall(reactor.callInThread, 
                self.check_for_changes)
        self.remote_checker.start(30)

    def check_for_changes(self):
        logging.debug("Checking linkmotime...")
        latest_snapshot = self.tahoe.get_latest_snapshot(self.remote_dircap)
        if latest_snapshot > self.parent.local_snapshot:
            self.parent.sync(latest_snapshot)

    def stop(self):
        self.remote_checker.stop()

