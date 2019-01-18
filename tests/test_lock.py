# -*- coding: utf-8 -*-

import os

import pytest

from gridsync.lock import Lock


def test_lock_acquire(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert lock.fd


def test_lock_acquire_filepath_created(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    assert os.path.isfile(lock.filepath)


def test_lock_acquire_raise_oserror_on_second_call(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    with pytest.raises(OSError):
        lock.acquire()


def test_lock_acquire_raise_oserror_from_second_instance(tmpdir):
    lock_1 = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock_1.acquire()
    lock_2 = Lock(os.path.join(str(tmpdir), 'test.lock'))
    with pytest.raises(OSError):
        lock_2.acquire()


def test_lock_release(tmpdir):
    lock = Lock(os.path.join(str(tmpdir), 'test.lock'))
    lock.acquire()
    lock.release()
    lock.acquire()
    lock.release()
