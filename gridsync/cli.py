#!/usr/bin/env python2
# vim:fileencoding=utf-8:ft=python

from __future__ import unicode_literals

import os
import sys
import time
import signal
import socket
import argparse
import threading

from twisted.internet.error import CannotListenError

import server

from config import Config
from tahoe import Tahoe
from watcher import Watcher
from gui import main_window


__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)


def send_command(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 52045))
        s.send(command)
        sys.exit()
    except Exception as e:
        print(str(e))

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    parser = argparse.ArgumentParser(
            description='Synchronize local directories with remote Tahoe-LAFS storage grids.',
            epilog='Example: %(prog)s <URI>')
    parser.add_argument('command', nargs='?', help='Command to send (e.g., "stop", "reload", "sync").')
    parser.add_argument('-g', '--no-gui', action='store_true', help='Run without GUI.')
    parser.add_argument('-t', '--use-tor', action='store_true', help='Run with Tor (requires torsocks)')
    parser.add_argument('-c', '--config', metavar='', nargs=1, help='Load settings from config file.')
    parser.add_argument('--version', action="version", version='%(prog)s ' + __version__)
    args = parser.parse_args()
    #print args

    try:
        server.start()
    except CannotListenError:
        if args.command:
            send_command(args.command)
        else:
            sys.exit("Gridsync already running.")
    
     
    
    config = Config()
    settings = config.load()
    tahoe_objects = []
    watcher_objects = []
    for node_name, node_settings in settings['tahoe_nodes'].items():
        t = Tahoe(os.path.join(config.config_dir, node_name), node_settings)
        tahoe_objects.append(t)
        for sync_name, sync_settings in settings['sync_targets'].items():
            if sync_settings[0] == node_name:
                w = Watcher(t, os.path.expanduser(sync_settings[1]), sync_settings[2])
                watcher_objects.append(w)
    g = threading.Thread(target=main_window.main)
    g.setDaemon(True)
    #g.start()
    
    threads = [threading.Thread(target=o.start) for o in tahoe_objects]
    [t.start() for t in threads]
    [t.join() for t in threads]

    time.sleep(1)

    threads = [threading.Thread(target=o.start) for o in watcher_objects]
    [t.start() for t in threads]
    [t.join() for t in threads]
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        threads = [threading.Thread(target=o.stop) for o in watcher_objects]
        [t.start() for t in threads]
        [t.join() for t in threads]
        
        threads = [threading.Thread(target=o.stop) for o in tahoe_objects]
        [t.start() for t in threads]
        [t.join() for t in threads]
        
        config.save(settings)
        sys.exit()


if __name__ == "__main__":
    main()

