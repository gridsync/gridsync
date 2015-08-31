# -*- coding: utf-8 -*-

import os
import tempfile

from gridsync.tahoe import bin_tahoe, Tahoe


def test_bin_tahoe_exists():
    assert bin_tahoe()

def test_bin_tahoe_is_executable():
    assert os.access(bin_tahoe(), os.X_OK)


class TestTahoe():
    def setup_class(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tahoe = Tahoe(self.tmp_dir)

    def test_init(self):
        assert self.tahoe

    def test_name(self):
        assert self.tahoe.name

    def test_node_dir_exists(self):
        assert os.path.isdir(self.tahoe.node_dir)

    def test_tahoe_version_1_10_or_greater(self):
        assert self.tahoe.version() > '1.10'

