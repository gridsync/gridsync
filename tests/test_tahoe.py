from gridsync.tahoe import *

def setup_module():
    print 'setup'

def test_print():
    assert 1 == 2

def teardown_module():
    print 'teardown'
