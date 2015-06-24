from gridsync.utils import *

def test__utc_to_epoch():
    assert utc_to_epoch("2015-06-16_02:48:40Z") == 1434437320

