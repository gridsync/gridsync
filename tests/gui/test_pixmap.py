"""
Tests for ``gridsync.gui.pixmap``.
"""

from gridsync import resource
from gridsync.gui.pixmap import BadgedPixmap


def test_badged_pixmap():
    bp = BadgedPixmap(resource("gridsync.png"), "test")
    assert bp is not None
