from gridsync.uri import *

def test_remove_prefix():
    assert remove_prefix("gridsync://test") == "test"

