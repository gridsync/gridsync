#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import subprocess
import sys
from typing import Optional, Sequence, Union

from gridsync import APP_NAME
from gridsync import __doc__ as description
from gridsync import __version__, msg
from gridsync.core import Core
from gridsync.errors import FilesystemLockError


class TahoeVersion(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Union[str, Sequence, None],
        option_string: Optional[str] = None,
    ) -> None:
        subprocess.call(["tahoe", "--version-and-path"])
        sys.exit()


def main() -> Union[int, str]:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--debug", action="store_true", help="Print debug messages to STDOUT."
    )
    parser.add_argument(
        "--tahoe-version",
        nargs=0,
        action=TahoeVersion,
        help="Call 'tahoe --version-and-path' and exit. For debugging.",
    )
    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s " + __version__
    )

    try:
        Core(parser.parse_args()).start()
    except FilesystemLockError:
        msg.critical(
            "{} already running".format(APP_NAME),
            "{} is already running.".format(APP_NAME),
        )
        return "ERROR: {} is already running.".format(APP_NAME)
    return 0


if __name__ == "__main__":
    sys.exit(main())
