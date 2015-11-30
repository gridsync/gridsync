# -*- coding: utf-8 -*-

import os
import tempfile

import pytest

from gridsync.tahoe import DEFAULT_SETTINGS, bin_tahoe, Tahoe


class TestTahoe():
    def setup_class(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.tahoe = Tahoe(self.tmp_dir)
        #print 'TMP_DIR: '+self.tmp_dir

    def test_init(self):
        assert self.tahoe

    def test_name(self):
        assert self.tahoe.name

    #def test_node_dir_exists(self):
    #    assert os.path.isdir(self.tahoe.node_dir)

    #def test_tahoe_version(self):
    #    assert self.tahoe.command(['--version'])

    #def test_tahoe_version_1_10_or_greater(self):
    #    assert self.tahoe.command(['--version']).split()[1] > '1.10'

    #def test_tahoe_create(self):
    #    self.tahoe.command(['create-client'])
    #    assert os.path.isfile(os.path.join(self.tahoe.node_dir, 'tahoe.cfg'))

    #def test_tahoe_get_config(self):
    #    assert self.tahoe.get_config('client', 'introducer.furl') == 'None'

    #def test_tahoe_set_config(self):
    #    self.tahoe.set_config('node', 'web.port', '55555')
    #    assert self.tahoe.get_config('node', 'web.port') == '55555'

    #def test_tahoe_add_default_settings(self):
    #    self.tahoe.settings = DEFAULT_SETTINGS
    #    assert self.tahoe.settings == DEFAULT_SETTINGS

    #def test_tahoe_setup(self):
    #    self.tahoe.setup(self.tahoe.settings)
    #    assert self.tahoe.get_config('client', 'shares.total') == '1'
   # 
    #def test_tahoe_start(self):
    #    self.tahoe.command(['start'])
    #    assert open(os.path.join(self.tahoe.node_dir, 'twistd.pid')).read()

    #def test_tahoe_command_add_alias(self):
    #    assert self.tahoe.command(['add-alias', 'test', 'URI:DIR2:ueffj5x2rmgorwbdyfahirxwtu:jawtp4t46embauvojb75f6tagniedpi5tuvdllndolpa4ybjkj4a']) == "Alias 'test' added"

    #def test_get_aliases(self):
    #    assert self.tahoe.get_aliases()

    #def test_get_dircap_from_alias(self):
    #    assert self.tahoe.get_dircap_from_alias('test') == 'URI:DIR2:ueffj5x2rmgorwbdyfahirxwtu:jawtp4t46embauvojb75f6tagniedpi5tuvdllndolpa4ybjkj4a'

    #def test_get_alias_from_dircap(self):
    #    assert self.tahoe.get_alias_from_dircap('URI:DIR2:ueffj5x2rmgorwbdyfahirxwtu:jawtp4t46embauvojb75f6tagniedpi5tuvdllndolpa4ybjkj4a') == 'test:'

    #def test_aliasify_dircap(self):
    #    assert self.tahoe.aliasify('URI:DIR2:ueffj5x2rmgorwbdyfahirxwtu:jawtp4t46embauvojb75f6tagniedpi5tuvdllndolpa4ybjkj5a') == 'f1cd75987ea516963e55f8ae37e67ae20336ebb7eafd90aeff30986e644a44ba:'

    #def test_aliasify_alias(self):
    #    assert self.tahoe.aliasify('test:') == 'test:'

    #def test_aliasify_alias_invalid(self):
    #    with open(os.path.join(self.tahoe.node_dir, 'private', 'aliases'), 'w') as f:
    #        f.write('invalid_alias: invalid_dircap')
    #    with pytest.raises(ValueError):
    #        invalid = self.tahoe.aliasify('invalid_alias:')

    #def test_aliasify_alias_not_found(self):
    #    os.remove(os.path.join(self.tahoe.node_dir, 'private', 'aliases'))
    #    with pytest.raises(LookupError):
    #        not_found = self.tahoe.aliasify('test_not_found')

    #def teardown_class(self):
    #    self.tahoe.command(['stop'])
