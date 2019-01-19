# -*- coding: utf-8 -*-

import os

import pytest

from gridsync.lock import FilesystemLock
from gridsync.errors import FilesystemLockError


def test_lock_acquire(tmpdir):
    lock = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert lock.fd


def test_lock_acquire_filepath_created(tmpdir):
    lock = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert os.path.isfile(lock.filepath)


def test_lock_acquire_raise_filesystemlockerror_on_second_call(tmpdir):
    lock = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    with pytest.raises(FilesystemLockError):
        lock.acquire()


def test_lock_acquire_raise_filesystemlockerror_from_second_instance(tmpdir):
    lock_1 = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    lock_1.acquire()
    lock_2 = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    with pytest.raises(FilesystemLockError):
        lock_2.acquire()


def test_lock_release(tmpdir):
    lock = FilesystemLock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    lock.release()
    lock.acquire()
    lock.release()
