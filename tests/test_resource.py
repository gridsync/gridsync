import os
import sys

from gridsync.resource import resource


def test_resource():
    import gridsync.resource
    basepath = os.path.dirname(os.path.realpath(gridsync.resource.__file__))
    assert resource('test') == os.path.join(basepath, 'resources', 'test')


def test_resource_frozen(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    basepath = os.path.dirname(os.path.realpath(sys.executable))
    assert resource('test') == os.path.join(basepath, 'resources', 'test')
