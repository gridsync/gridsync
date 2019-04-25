# -*- coding: utf-8 -*-

import pytest

from gridsync.gui.font import Font


@pytest.mark.parametrize(
    'platform,expected',
    [
        ('darwin', 16),
        ('linux', 12),
        ('win32', 12),
    ]
)
def test_font_default(platform, expected, monkeypatch):
    monkeypatch.setattr('sys.platform', platform)
    font = Font()
    assert font.pointSize() == expected


@pytest.mark.parametrize(
    'point_size,point_size_mac',
    [
        (8, 11),
        (9, 12),
        (10, 13),
        (11, 15),
        (12, 16),
        (14, 18),
        (16, 20),
        (18, 22),
    ]
)
def test_font_upscale_on_macos(point_size, point_size_mac, monkeypatch):
    monkeypatch.setattr('sys.platform', 'darwin')
    font = Font(point_size)
    assert font.pointSize() == point_size_mac
