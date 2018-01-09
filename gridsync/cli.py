#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys

from twisted.internet.error import CannotListenError

from gridsync import APP_NAME
from gridsync import __doc__ as description
from gridsync._version import __version__
from gridsync.core import Core
from gridsync import msg


class TahoeVersion(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        import subprocess
        subprocess.call(['tahoe', '--version-and-path'])
        sys.exit()


def main():
    parser = argparse.ArgumentParser(
        description=description)
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print debug messages to STDOUT.')
    parser.add_argument(
        '--tahoe-version',
        nargs=0,
        action=TahoeVersion,
        help="Call 'tahoe --version-and-path' and exit. For debugging.")
    parser.add_argument(
        '-V',
        '--version',
        action="version",
        version='%(prog)s ' + __version__)
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            format='%(asctime)s %(levelname)s %(funcName)s %(message)s',
            level=logging.DEBUG, stream=sys.stdout)
        from twisted.python.log import startLogging
        startLogging(sys.stdout)
    #else:
    #    appname = settings['application']['name']
    #    logfile = os.path.join(config_dir, '{}.log'.format(appname))
    #    logging.basicConfig(
    #        format='%(asctime)s %(levelname)s %(funcName)s %(message)s',
    #        level=logging.INFO, filename=logfile)

    try:
        core = Core(args)
        core.start()
    except CannotListenError:
        msg.critical(
            "{} already running".format(APP_NAME),
            "{} is already running.".format(APP_NAME))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
