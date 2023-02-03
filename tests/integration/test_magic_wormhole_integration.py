import pytest


def test_wormhole_mailbox_listening_on_localhost(wormhole_mailbox):
    assert wormhole_mailbox.startswith("ws://localhost:")
