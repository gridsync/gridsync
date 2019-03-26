# -*- coding: utf-8 -*-

"""
Support for reading the streaming Eliot logs available from a Tahoe-LAFS
node.
"""

class StreamedLogs():
    _started = False

    def __init__(self, gateway):
        self._gateway = gateway

    def start(self):
        if not self._started:
            self._started = True
