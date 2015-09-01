# -*- coding: utf-8 -*-

import os
import tempfile

from gridsync.tahoe import DEFAULT_SETTINGS, bin_tahoe, Tahoe


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

    def test_tahoe_version(self):
        assert self.tahoe.version()
    
    def test_tahoe_version_1_10_or_greater(self):
        assert self.tahoe.version() > '1.10'

    def test_tahoe_create(self):
        self.tahoe.create()
        assert os.path.isfile(os.path.join(self.tahoe.node_dir, 'tahoe.cfg'))

    def test_tahoe_get_config(self):
        assert self.tahoe.get_config('client', 'introducer.furl') == 'None'

    def test_tahoe_set_config(self):
        self.tahoe.set_config('node', 'web.port', '55555')
        assert self.tahoe.get_config('node', 'web.port') == '55555'
    
    def test_tahoe_add_default_settings(self):
        self.tahoe.settings = DEFAULT_SETTINGS
        assert self.tahoe.settings == DEFAULT_SETTINGS

    def test_tahoe_setup(self):
        self.tahoe.setup(self.tahoe.settings)
        assert self.tahoe.get_config('client', 'shares.total') == '1'
    
    def test_tahoe_start(self):
        self.tahoe.start()
        assert open(os.path.join(self.tahoe.node_dir, 'twistd.pid')).read()
    
    def test_tahoe_node_url(self):
        assert self.tahoe.node_url().startswith('http://127.0.0.1:')

    def test_tahoe_command_add_alias(self):
        assert self.tahoe.command(['add-alias', 'test', 'URI:DIR2:ueffj5x2rmgorwbdyfahirxwtu:jawtp4t46embauvojb75f6tagniedpi5tuvdllndolpa4ybjkj4a']) == "Alias 'test' added"

