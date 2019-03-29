import os.path
from base64 import b64encode
from functools import partial

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import pytest

from gridsync.tahoe import Tahoe


@pytest.fixture()
def reactor():
    return Mock()


def _tahoe(tmpdir_factory, reactor):
    client = Tahoe(str(tmpdir_factory.mktemp('tahoe')), executable='tahoe_exe', reactor=reactor)
    with open(os.path.join(client.nodedir, 'tahoe.cfg'), 'w') as f:
        f.write('[node]\nnickname = default')
    with open(os.path.join(client.nodedir, 'icon.url'), 'w') as f:
        f.write('test_url')
    private_dir = os.path.join(client.nodedir, 'private')
    os.mkdir(private_dir)
    with open(os.path.join(private_dir, 'aliases'), 'w') as f:
        f.write('test_alias: test_cap')
    with open(os.path.join(private_dir, 'magic_folders.yaml'), 'w') as f:
        f.write("magic-folders:\n  test_folder: {directory: test_dir}")
    client.set_nodeurl('http://example.invalid:12345/')
    with open(os.path.join(client.nodedir, 'node.url'), 'w') as f:
        f.write('http://example.invalid:12345/')
    with open(os.path.join(private_dir, 'api_auth_token'), 'w') as f:
        f.write(b64encode(b'a' * 32).decode('ascii'))
    return client


@pytest.fixture()
def tahoe_factory(tmpdir_factory):
    return partial(_tahoe, tmpdir_factory)


@pytest.fixture()
def tahoe(tmpdir_factory, reactor):
    return _tahoe(tmpdir_factory, reactor)
