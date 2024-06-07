from mnemonic import Mnemonic


def to_mnemonic(b: bytes) -> list[str]:
    return Mnemonic(language="english").to_mnemonic(b).split(" ")


def to_entropy(mnemonic: list[str]) -> bytes:
    return bytes(Mnemonic(language="english").to_entropy(mnemonic))


wordlist = Mnemonic(language="english").wordlist
