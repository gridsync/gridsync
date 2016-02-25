# -*- coding: utf-8 -*-

import os
import yaml

from gridsync.config import Config
from gridsync.tahoe import decode_introducer_furl


PROVIDERS = {
    'Tahoe-LAFS Public Test Grid': {
        'introducer.furl': "pb://hckqqn4vq5ggzuukfztpuu4wykwefa6d@publictestgrid.twilightparadox.com:50213,publictestgrid.lukas-pirl.de:50213,publictestgrid.e271.net:50213,198.186.193.74:50213,68.34.102.231:50213/introducer",
        'description': "A public storage grid run by members of the Tahoe-LAFS community. This storage grid is inteded to be used primarily for testing purposes and makes no guarantees with regard to availability; don't store any data in the pubgrid if losing it would cause trouble.",
        'homepage': "https://tahoe-lafs.org/trac/tahoe-lafs/wiki/TestGrid",
        'logo': ":tahoe-lafs.png"
    },
    'test.gridsync.io': {
        'introducer.furl': "pb://3kzbib3v5i7gmtd2vkjujfywqiwzintw@test.gridsync.io:44800/2qdq2buyzmwq6xuxl2sdzyej5vswhkqs",
        'description': "A test grid maintained by the developer(s) of Gridsync. Part of the Gridsync testing infrastructure, this storage grid has high availability but very low capacity; use this for testing purposes only as its shares will be flushed every 72 hours.",
        'homepage': "https://gridsync.io",
        'logo': ":gridsync.png"
    }
}


def create_storage_providers_db():
    providers_db = os.path.join(Config().config_dir, 'storage-providers.yml')
    print(providers_db)
    with open(providers_db, 'w') as f:
        try:
            os.chmod(providers_db, 0o600)
        except:
            pass
        yaml.safe_dump(PROVIDERS, f, encoding='utf-8', allow_unicode=True,
                indent=4, default_flow_style=False)

def get_storage_providers():
    providers_db = os.path.join(Config().config_dir, 'storage-providers.yml')
    try:
        with open(providers_db) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        create_storage_providers_db()
        return PROVIDERS

def add_storage_provider(introducer_furl, name=None, description=None):
    providers_db = os.path.join(Config().config_dir, 'storage-providers.yml')
    storage_providers = get_storage_providers()
    if not name:
        _, connection_hints = decode_introducer_furl(introducer_furl)
        name = connection_hints.split(',')[0].split(':')[0]
    new_provider = {}
    new_provider[name] = {
        'introducer.furl': introducer_furl,
        'description': description
    }
    storage_providers.update(new_provider)
    print(storage_providers)
    with open(providers_db, 'w') as f:
        try:
            os.chmod(providers_db, 0o600)
        except:
            pass
        yaml.safe_dump(storage_providers, f, encoding='utf-8',
                allow_unicode=True, indent=4, default_flow_style=False)
