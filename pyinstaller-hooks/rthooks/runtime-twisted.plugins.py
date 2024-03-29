"""
Runtime PyInstaller hook that patches :py:`twisted.plugin.getCache` to read
from the ``dropin.cache`` generated by associated build hook.
"""

import pickle
import sys
import os
from twisted import plugin

cache_path = os.path.join(sys._MEIPASS, 'twisted/plugins/dropin.cache')

plugin_cache = None

def load_cache():
    global plugin_cache
    with open(cache_path, "rb") as fp:
        plugin_cache = pickle.load(fp)

def getCache(module):
    print(module.__name__)
    if module.__name__ == "twisted.plugins":
        if plugin_cache is None:
            load_cache()
        return plugin_cache
    return {}

plugin.getCache = getCache
