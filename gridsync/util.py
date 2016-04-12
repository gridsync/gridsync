# -*- coding: utf-8 -*-

from __future__ import division


def h2b(s):
    """Convert 'human-readable' byte-representation to an integer of bytes"""
    for i, unit in enumerate(['KB', 'MB', 'GB', 'TB', 'PB', 'EB'], start=1):
        if s.endswith(unit):
            return int(float(s[:-2].strip()) * 1024 ** i)
    return int(s[:-1])


def b2h(b):
    """Convert integer of bytes into 'human-readable' byte-representation"""
    for i, unit in enumerate(['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
        rounded = round(b / (1024 ** i), 2)
        if rounded < 1024:
            return "{} {}".format(rounded, unit)
