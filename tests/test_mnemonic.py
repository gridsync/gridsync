from secrets import token_bytes

from mnemonic import Mnemonic

from gridsync.mnemonic import to_entropy, to_mnemonic


def test_to_entropy():
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


def test_jp() -> None:
    entropy = token_bytes(16)
    mnemonic = Mnemonic("japanese").to_mnemonic(entropy)

    phrase = mnemonic.split("\u3000")
    print(phrase)

    entropy2 = Mnemonic("japanese").to_entropy(phrase)

    assert entropy == entropy2
