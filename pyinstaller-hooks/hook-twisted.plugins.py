"""
PyInstaller hook that generates :py:`twisted.plugins`' :file:`dropin.cache`
for requested plugins.
"""
from binascii import a2b_base64
import json
import os

from PyInstaller.config import CONF
from PyInstaller.utils.hooks import exec_statement


def hook(api):
    # Get the list of all installed twisted plugin modules.
    modules = json.loads(
        exec_statement(
            """
        import json
        import sys
        from twisted import plugins
        from twisted.plugin import getCache

        json.dump(list(getCache(plugins).keys()), sys.stdout)
    """
        )
    )
    # Get the list twisted plugins that are referred to
    # by pyinstaller.
    # TODO: This should be configurable via pyinstaller's
    # hook config, once we are on a new enough version.
    included_modules = [
        module
        for module in modules
        if api.graph.findNode("twisted.plugins.{}".format(module))
    ]
    # Generate the dropin.cache for the referenced plugins.
    cache = exec_statement(
        """
        from binascii import b2a_base64
        import pickle
        import sys
        from twisted import plugins
        from twisted.plugin import getCache

        wanted_modules = set(%r)
        cache = {
            module: plugin for (module, plugin) in getCache(plugins).items()
            if module in wanted_modules
        }
        sys.stdout.buffer.write(b2a_base64(pickle.dumps(cache)))
        """
        % (included_modules,)
    )
    # Write the plugin somewhere that pyinstaller can pick it up and
    # request it be packaged.
    cache_path = os.path.join(CONF["workpath"], "dropin.cache")
    with open(cache_path, "wb") as fp:
        fp.write(a2b_base64(cache))
    api.add_datas([(cache_path, "twisted/plugins")])
