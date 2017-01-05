import os
import sys


def resource(filename):
    if getattr(sys, 'frozen', False):
        basepath = os.path.dirname(os.path.realpath(sys.executable))
    else:
        basepath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(basepath, 'resources', filename)
