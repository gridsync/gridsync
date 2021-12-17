"""
Tests for ``gridsync.gui.usage``.
"""

from gridsync.gui.usage import UsageView


def test_initial_state(fake_tahoe, gui):
    """
    When ``UsageView`` is first instantiated the storage-time indicators are
    hidden and the "loading" label is visible.
    """
    view = UsageView(fake_tahoe, gui)
    view.groupbox.parent().show()
    assert view.loading_storage_time.isVisible()
    assert not view.title.isVisible()
    assert not view.zkaps_required_label.isVisible()
    assert not view.chart_view.isVisible()


def test_on_zkaps_updated_some_remaining(fake_tahoe, gui):
    """
    After ``UsageView.on_zkaps_updated`` is called indicating there are some
    ZKAPs, the storage-time indicators are visible and the "loading" label is
    hidden.
    """
    view = UsageView(fake_tahoe, gui)
    view.groupbox.parent().show()
    view.on_zkaps_updated(0, 100)
    assert not view.loading_storage_time.isVisible()
    assert view.title.isVisible()
    assert not view.zkaps_required_label.isVisible()
    assert view.chart_view.isVisible()


def test_on_zkaps_updated_none_remaining(fake_tahoe, gui):
    """
    After ``UsageView.on_zkaps_updated`` is called indicating there are no
    more ZKAPs, "ZKAPs required" label is visible and the storage-time
    indicators and "loading" label are hidden.
    """
    view = UsageView(fake_tahoe, gui)
    view.groupbox.parent().show()
    view.on_zkaps_updated(100, 0)
    assert not view.loading_storage_time.isVisible()
    assert not view.title.isVisible()
    assert view.zkaps_required_label.isVisible()
    assert not view.chart_view.isVisible()
