#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from __future__ import unicode_literals

import os
import sys
import time

from gridsync.config import Config
from gridsync.tahoe import Tahoe
from gridsync.watcher import Watcher


def check_pid(pid):        
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def is_process_running(process_id):
    try:
        os.kill(process_id, 0)
        return True
    except OSError:
        return False


pid = str(os.getpid())
pidfile = "/tmp/mydaemon.pid"

if os.path.isfile(pidfile):
    print "%s already exists, exiting" % pidfile
    sys.exit()
else:
    file(pidfile, 'w').write(pid)

# Do some actual work here

os.unlink(pidfile)

class Daemon():
    def __init__(self):
        if os.name == 'nt':
            self.gridsync_dir = os.path.join(os.getenv('APPDATA'), 'gridsync')
        else:
            self.gridsync_dir = os.path.join(os.path.expanduser('~'), '.config', 'gridsync')

        

        if not os.path.isfile(os.path.join(self.gridsync_dir, 'gridsync.pid')):
            self.command('start')
        else:
            pid = int(open(os.path.join(self.tahoe_path, 'twistd.pid')).read())
            try:
                os.kill(pid, 0)
            except OSError:
                self.command('start')









def main():
    config = Config()
    settings = config.load()
    tahoe_objects = []
    watcher_objects = []
    for node_name, node_settings in settings['tahoe_nodes'].items():
        t = Tahoe(os.path.join(config.config_dir, node_name), node_settings)
        tahoe_objects.append(t)
        for sync_name, sync_settings in settings['sync'].items():
            if sync_settings[0] == node_name:
                w = Watcher(t, os.path.expanduser(sync_settings[1]), sync_settings[2])
                watcher_objects.append(w)

    for t in tahoe_objects:
        t.start()

    for w in watcher_objects:
        w.sync()
        w.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nshutting down!')
        for w in watcher_objects:
            w.stop()
        for t in tahoe_objects:
            t.stop()
        config.save(settings)
        sys.exit()


if __name__ == "__main__":
    main()

