"""
PyInstaller hook that implements the ``__path__`` extending
logic in :py:`twisted.plugin`.
"""

import os

def pre_safe_import_module(api):
    for path in api.module_graph.path:
        package_dir = os.path.join(path, 'twisted', 'plugins')
        if os.path.exists(package_dir):
            print("Adding '{}' to PyInstaller search path for 'twisted.plugins'.".format(package_dir))
            api.append_package_path(package_dir)
