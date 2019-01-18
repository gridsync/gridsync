# -*- coding: utf-8 -*-

import logging
import os
import sys

try:
    import fcntl
except ImportError:  # win32
    pass


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
            fd = os.open(self.filepath, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        else:
            fd = open(self.filepath, 'w')
            fd.flush()
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
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
