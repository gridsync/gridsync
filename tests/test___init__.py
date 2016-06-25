import difflib
import os
import sys
if sys.version_info >= (3, 4):
    from importlib import reload

import gridsync


def test_the_approval_of_RMS():  # :)
    assert gridsync.__license__.startswith('GPL')


def test_frozen_init_del_reactor(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    sys.modules['twisted.internet.reactor'] = 'test'
    reload(gridsync)
    assert 'twisted.internet.reactor' not in sys.modules


def test_frozen_init_append_tahoe_bundle_to_PATH(monkeypatch):
    monkeypatch.setattr("sys.frozen", True, raising=False)
    old_path = os.environ['PATH']
    reload(gridsync)
    delta = ''
    for _, s in enumerate(difflib.ndiff(old_path, os.environ['PATH'])):
        if s[0] == '+':
            delta += s[-1]
    assert delta == os.pathsep + os.path.join(os.path.dirname(sys.executable),
                                              'Tahoe-LAFS')
