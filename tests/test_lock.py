# -*- coding: utf-8 -*-

import os

import pytest

from gridsync.lock import Lock


def test_lock_acquire(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock._acquire()
    assert lock.fd


def test_lock_acquire_lockfile_created(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock._acquire()
    assert os.path.isfile(lock.lockfile)


def test_lock_acquire_raise_oserror(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock._acquire()
    with pytest.raises(OSError):
        lock._acquire()


def test_lock_release_lockfile_removed(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock._acquire()
    lock._release()
    assert not os.path.isfile(lock.lockfile)
