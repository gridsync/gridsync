"""
Tests for ``gridsync.gui.pixmap``.
"""

from qtpy.QtGui import QPixmap

from gridsync import resource
from gridsync.gui.pixmap import BadgedPixmap, CompositePixmap, Pixmap


def test_pixmap():
    p = Pixmap(resource("gridsync.png"), 16)
    size = p.size()
    assert (size.width(), size.height()) == (16, 16)


def test_composite_pixmap(gui):
    original = QPixmap(resource("gridsync.png"))
    composite = CompositePixmap(original, "gridsync.png", grayout=True)
    assert composite != original


def test_badged_pixmap(gui):
    original = QPixmap(resource("gridsync.png"))
    badged = BadgedPixmap(original, "test")
    assert badged != original
