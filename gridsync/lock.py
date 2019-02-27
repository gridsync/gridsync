# -*- coding: utf-8 -*-

import logging
import os
import sys

try:
    import fcntl
except ImportError:  # win32
    pass

from gridsync.errors import FilesystemLockError


class FilesystemLock():
    def __init__(self, filepath):
        self.filepath = filepath
        self.fd = None

    def acquire(self):
        logging.debug("Acquiring lock: %s ...", self.filepath)
        if sys.platform == 'win32':
            try:
                os.remove(self.filepath)
            except OSError:
                pass
            try:
                fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError as error:
                if error.errno == 17:  # File exists
                    raise FilesystemLockError(
                        "Could not acquire lock on {}: {}".format(
                            self.filepath, str(error)))
                raise
        else:
            fd = open(self.filepath, 'w')
            fd.flush()
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as error:
                raise FilesystemLockError(
                    "Could not acquire lock on {}: {}".format(
                        self.filepath, str(error)))
        self.fd = fd
        logging.debug("Acquired lock: %s", self.fd)

    def release(self):
        logging.debug("Releasing lock: %s ...", self.filepath)
        if not self.fd:
            logging.warning("No file descriptor found")
        elif sys.platform == 'win32':
            os.close(self.fd)
        else:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        logging.debug("Lock released: %s", self.filepath)
        try:
            os.remove(self.filepath)
        except OSError:
            pass
