import sys
import socket
import argparse
import subprocess

from twisted.internet.error import CannotListenError

#import allmydata
#import zfec
#import simplejson
#import foolscap
#import Crypto
#import mock
#import pycryptopp
#import nevow
#import twisted.python.reflect

from server import Server

__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)


def send_command(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", 52045))
        s.send(command)
        #sys.exit()
    except Exception as e:
        print(str(e))

def main():
    #signal.signal(signal.SIGINT, signal.SIG_DFL)
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
        output = subprocess.check_output(["tahoe", "-V"])
        tahoe = output.split('\n')[0]
        print("Found: " + tahoe)
    except OSError:
        sys.exit('Tahoe-LAFS installation not found.')


    try:
        gridsync = Server(args)
        gridsync.start()
    except CannotListenError:
        if args.command:
            send_command(args.command)
        else:
            pass
            #sys.exit("Gridsync already running.")


if __name__ == "__main__":
    main()
