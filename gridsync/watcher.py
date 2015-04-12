#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from __future__ import unicode_literals

import os
import shutil
import datetime
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class LocalEventHandler(FileSystemEventHandler):
    def __init__(self, tahoe, local_dir, remote_dircap):
        self.tahoe = tahoe
        self.local_dir = local_dir
        self.remote_dircap = remote_dircap
        if not os.path.isdir(self.local_dir):
            os.makedirs(self.local_dir)
        self.do_backup = False
        self.check_for_backup()

    def on_modified(self, event):
        self.do_backup = True
        print(event)

    def check_for_backup(self):
        t = threading.Timer(1.0, self.check_for_backup)
        t.setDaemon(True)
        t.start()
        if self.do_backup:
            self.do_backup = False
            self.tahoe.backup(self.local_dir, self.remote_dircap)


class Watcher():
    def __init__(self, tahoe, local_dir, remote_dircap):
        self.tahoe = tahoe
        self.local_dir = os.path.expanduser(local_dir)
        self.remote_dircap = remote_dircap
        if not os.path.isdir(self.local_dir):
            os.makedirs(self.local_dir)

    def start(self):
        print("*** Starting observer in %s" % self.local_dir)
        event_handler = LocalEventHandler(self.tahoe, self.local_dir, self.remote_dircap)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.local_dir, recursive=True)
        self.observer.start()

    def stop(self):
        print("*** Stopping observer in %s" % self.local_dir)
        try:
            self.observer.stop()
            self.observer.join()
        except:
            pass

    def _get_local_mtimes(self):
        local_mtimes = {}
        for root, dirs, files in os.walk(self.local_dir, followlinks=True):
            for name in files:
                fn = os.path.join(root, name)
                local_mtimes[fn] = os.path.getmtime(fn)
            for name in dirs:
                fn = os.path.join(root, name)
                local_mtimes[fn] = os.path.getmtime(fn)
        return local_mtimes

    def _create_conflicted_copy(self, file, mtime):
        base, extension = os.path.splitext(file)
        t = datetime.datetime.fromtimestamp(mtime)
        tag = t.strftime('.(conflicted copy %Y-%m-%d %H-%M-%S)')
        newname = base + tag + extension
        shutil.copy2(file, newname)

    def sync(self, snapshot='Latest'):
        local_dir = os.path.expanduser(self.local_dir)
        remote_dircap = '/'.join([self.remote_dircap, snapshot])
        local_mtimes = self._get_local_mtimes()
        remote_mtimes = self.tahoe.get_metadata(remote_dircap, metadata={})
        do_backup = False
        threads = []
        for file, metadata in remote_mtimes.items():
            if metadata['type'] == 'dirnode':
                dir = os.path.join(local_dir, file)
                if not os.path.isdir(dir):
                    os.makedirs(dir)
        for file, metadata in remote_mtimes.items():
            if metadata['type'] == 'filenode':
                file = os.path.join(local_dir, file)
                if file in local_mtimes:
                    local_mtime = int(local_mtimes[file])
                    remote_mtime = int(metadata['mtime']) # :/
                    if remote_mtime > local_mtime:
                        print("[@] %s older than stored version, scheduling download" % file)
                        self._create_conflicted_copy(file, local_mtime)
                        threads.append(
                                threading.Thread(
                                    target=self.tahoe.get, 
                                    args=(metadata['uri'], file, remote_mtime)))
                    elif remote_mtime < local_mtime:
                        print("[*] %s is newer than stored version, scheduling backup" % file)
                        do_backup = True
                    else:
                        print "[✓] %s is up to date." % file 
                else:
                    print("[?] %s is missing, scheduling download" % file)
                    threads.append(
                            threading.Thread(
                                target=self.tahoe.get, 
                                args=(metadata['uri'], file, metadata['mtime'])))
        for file, metadata in local_mtimes.items():
            if file.split(local_dir + os.path.sep)[1] not in remote_mtimes:
                print("[!] %s isn't stored, scheduling backup" % file)
                do_backup = True
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if do_backup:
            self.tahoe.backup(self.local_dir, self.remote_dircap)

