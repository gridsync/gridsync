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

    def _acquire_win32(self):
        try:
            os.remove(self.lockfile)
        except OSError:
            pass
        fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        self.fd = fd

    def _acquire(self):
        fd = open(self.lockfile, 'w')
        fd.flush()
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.fd = fd

    def acquire(self):
        logging.debug("Acquiring lock: %s ...", self.lockfile)
        if sys.platform == 'win32':
            self._acquire_win32()
        else:
            self._acquire()
        logging.debug("Acquired lock: %s", self.fd)

    def _release_win32(self):
        if self.fd:
            os.close(self.fd)

    def _release(self):
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)

    def release(self):
        logging.debug("Releasing lock: %s ...", self.lockfile)
        if sys.platform == 'win32':
            self._release_win32()
        else:
            self._release()
        logging.debug("Lock released.")
        #try:
        #    os.remove(self.lockfile)
        #except OSError:
        #    pass
