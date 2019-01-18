# -*- coding: utf-8 -*-

import os

import pytest

from gridsync.lock import Lock


def test_lock_acquire(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert lock.fd


def test_lock_acquire_lockfile_created(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert os.path.isfile(lock.lockfile)


def test_lock_acquire_raise_oserror(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    with pytest.raises(OSError):
        lock.acquire()


def test_lock_release(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    lock.release()
    lock.acquire()
    lock.release()
