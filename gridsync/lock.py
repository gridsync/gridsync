# -*- coding: utf-8 -*-

import logging
import os
import sys

try:
    import fcntl
except ImportError:  # win32
    pass


class Lock():
    def __init__(self, lockfile):
        self.lockfile = lockfile
        self.fd = None

    def acquire(self):
        logging.debug("Acquiring lock: %s ...", self.lockfile)
        if sys.platform == 'win32':
            try:
                os.remove(self.lockfile)
            except OSError:
                pass
            fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        else:
            fd = open(self.lockfile, 'w')
            fd.flush()
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.fd = fd
        logging.debug("Acquired lock: %s", self.fd)

    def release(self):
        logging.debug("Releasing lock: %s ...", self.lockfile)
        if not self.fd:
            logging.warning("No file descriptor found")
        elif sys.platform == 'win32':
            os.close(self.fd)
        else:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        logging.debug("Lock released: %s", self.lockfile)
        try:
            os.remove(self.lockfile)
        except OSError:
            pass
