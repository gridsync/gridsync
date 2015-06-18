from __future__ import unicode_literals

import time
import datetime


def utc_to_epoch(timestamp):
    t = datetime.datetime.strptime(timestamp[:-1], "%Y-%m-%d_%H:%M:%S")
    return int(time.mktime(t.timetuple()))

def epoch_to_utc(timestamp):
    pass


#print(utc_to_epoch("2015-06-16_02:48:40Z"))
