# -*- coding: utf-8 -*-

from gridsync.util import h2b, b2h


class TestUtil():
    def test_1B_2b(self):
        assert h2b('1B') == 1

    def test_1024B_2b(self):
        assert h2b('1KB') == 1024

    def test_256GB_2b(self):
        assert h2b('256GB') == 274877906944

    def test_274877906944_2h(self):
        assert b2h(274877906944) == '256.0 GB'

    def test_1024_2h(self):
        assert b2h(1024) == '1.0 KB'

    def test_1_2h(self):
        assert b2h(1) == '1.0 B'

