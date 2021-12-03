# Do nothing hook to override the hook from pyinstaller_hooks_contrib
# Since gridsync installs a reactor manually, we don't want the hook
# installing the default reactor on us.

# This can be removed if/once
# https://github.com/pyinstaller/pyinstaller-hooks-contrib/pull/356
# is released.
