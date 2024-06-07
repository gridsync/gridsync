from gridsync.phrase import to_entropy, to_mnemonic


def test_to_bytes():
    assert (
        to_entropy(
            [
                "coral",
                "light",
                "army",
                "gather",
                "adapt",
                "blossom",
                "school",
                "alcohol",
                "coral",
                "light",
                "army",
                "giggle",
            ]
        )
        == b"0" * 16
    )


def test_to_mnemonic():
    assert to_mnemonic(b"0" * 16) == [
        "coral",
        "light",
        "army",
        "gather",
        "adapt",
        "blossom",
        "school",
        "alcohol",
        "coral",
        "light",
        "army",
        "giggle",
    ]
