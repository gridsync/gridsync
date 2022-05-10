import sys

from mypy.__main__ import console_entry
from qtpy import API

# Type-stubs for PyQt6 are currently incomplete, resulting in mypy
# throwing many `attr-defined` and `arg-type` errors when using PyQt6.
# Rather than suppressing those error codes globally (i.e., for PyQt5),
# disable them only under PyQt6, for now. This wrapper can/should be
# removed once the `PyQt6-stubs` project makes a PyPI release -- and/or
# once PyQt6 type-stubs are provided upstream. See/follow
# https://github.com/python-qt-tools/PyQt6-stubs
if API == "pyqt6":
    sys.argv.append("--disable-error-code=attr-defined")
    sys.argv.append("--disable-error-code=arg-type")

console_entry()
