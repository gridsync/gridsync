from gridsync.gui.toolbar import RecoveryMenuButton


def test_recovery_import_action_is_enabled_by_default() -> None:
    button = RecoveryMenuButton()
    assert button.import_action.isEnabled() is True


def test_recovery_export_action_is_disabled_by_default() -> None:
    button = RecoveryMenuButton()
    assert button.export_action.isEnabled() is False
