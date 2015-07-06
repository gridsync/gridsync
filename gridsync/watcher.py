# -*- coding: utf-8 -*-

import os
import time
import threading
import json
import logging

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import sync


class Watcher(PatternMatchingEventHandler):
    def __init__(self, parent, tahoe, local_dir, remote_dircap, polling_frequency=20):
        super(Watcher, self).__init__(ignore_patterns=["*.gridsync-versions*"])
        self.parent = parent
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        if not os.path.isdir(self.local_dir):
            os.makedirs(self.local_dir)
        self.polling_frequency = polling_frequency
        self.latest_snapshot = 0
        self.do_backup = False
        self.check_for_backup()

    def check_for_backup(self):
        if self.do_backup and not self.parent.sync_state:
            self.do_backup = False
            time.sleep(1)
            if not self.do_backup:
                self.parent.sync_state += 1
                latest_snapshot = self.get_latest_snapshot()
                if latest_snapshot == self.latest_snapshot:
                    self.tahoe.backup(self.local_dir, self.remote_dircap)
                else:
                    sync.sync(self.tahoe, self.local_dir, self.remote_dircap)
                # XXX Race condition
                self.latest_snapshot = self.get_latest_snapshot()
                self.parent.sync_state -= 1
                #notify.notify("Sync finished.")
        t = threading.Timer(1.0, self.check_for_backup)
        t.setDaemon(True)
        t.start()
    
    def on_modified(self, event):
        self.do_backup = True
        logging.debug(event)
        print event.src_path

    def start(self):
        #self.sync()
        self.check_for_updates()
        logging.info("Starting observer in %s" % self.local_dir)
        self.observer = Observer()
        self.observer.schedule(self, self.local_dir, recursive=True)
        self.observer.start()

    def stop(self):
        logging.info("Stopping observer in %s" % self.local_dir)
        try:
            self.observer.stop()
            self.observer.join()
        except:
            pass

    def check_for_updates(self):
        latest_snapshot = self.get_latest_snapshot()
        if latest_snapshot == self.latest_snapshot:
            logging.debug("Up to date ({}); nothing to do.".format(latest_snapshot))
        else:
            logging.debug("New snapshot available ({}); syncing...".format(latest_snapshot))
            # XXX self.parent.sync_state should probably be a list of syncpair 
            #objects
            # check here for sync_state
            self.parent.sync_state += 1
            sync.sync(self.tahoe, self.local_dir, self.remote_dircap)
            self.parent.sync_state -= 1
            # XXX Race condition
            self.latest_snapshot = latest_snapshot
        t = threading.Timer(self.polling_frequency, self.check_for_updates)
        t.setDaemon(True)
        t.start()

    def get_latest_snapshot(self):
        dircap = self.remote_dircap + "/Archives"
        out = self.tahoe.command_output("ls --json %s" % dircap)
        j = json.loads(out)
        snapshots = []
        for snapshot in j[1]['children']:
            snapshots.append(snapshot)
        snapshots.sort()
        return snapshots[-1:][0]
        #latest = snapshots[-1:][0]
        #return utils.utc_to_epoch(latest) 

