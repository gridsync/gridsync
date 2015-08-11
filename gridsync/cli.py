#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import socket
import sys

# Workarounds for PyInstaller
if getattr(sys, 'frozen', False):
    del sys.modules['twisted.internet.reactor']
    if sys.platform == 'darwin':
        os.environ["PATH"] += os.pathsep + "/usr/local/bin" + os.pathsep \
                + "/Applications/tahoe.app/bin" + os.pathsep \
                + os.path.expanduser("~/Library/Python/2.7/bin") \
                + os.pathsep + os.path.dirname(sys.executable) \
                + '/Tahoe-LAFS/bin'

from twisted.internet.error import CannotListenError

from gridsync._version import __version__
from gridsync.server import Server


def send_command(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 52045))
        s.send(command)
        #sys.exit()
    except Exception as e:
        logging.error(str(e))

def main():
    parser = argparse.ArgumentParser(
            description='Synchronize local directories with Tahoe-LAFS storage grids.',
            epilog='Example: %(prog)s <URI>')
    parser.add_argument('command', nargs='*', help='Command to send (e.g., "stop", "reload", "sync").')
    parser.add_argument('-c', '--config', metavar='<file>', nargs=1, help='Load settings from config file.')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to STDOUT.')
    parser.add_argument('-g', '--no-gui', action='store_true', help='Run without GUI.')
    #parser.add_argument('-t', '--use-tor', action='store_true', help='Run with Tor (requires torsocks)')
    parser.add_argument('-V', '--version', action="version", version='%(prog)s ' + __version__)
    args = parser.parse_args()

    try:
        gridsync = Server(args)
        gridsync.start()
    except CannotListenError:
        if args.command:
            send_command(' '.join(args.command))
        else:
            sys.exit("Gridsync already running.")


if __name__ == "__main__":
    main()
