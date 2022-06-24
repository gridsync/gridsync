"""
Tests for ``gridsync.gui.pixmap``.
"""

from gridsync import resource
from gridsync.gui.pixmap import BadgedPixmap


def test_badged_pixmap(gui):
    bp = BadgedPixmap(resource("gridsync.png"))
    assert bp is not None
