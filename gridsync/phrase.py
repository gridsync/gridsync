from mnemonic import Mnemonic


def to_mnemonic(b: bytes, language: str = "english") -> list[str]:
    return Mnemonic(language=language).to_mnemonic(b).split(" ")


def to_entropy(mnemonic: list[str], language: str = "english") -> bytes:
    return bytes(Mnemonic(language=language).to_entropy(mnemonic))


wordlist = Mnemonic(language="english").wordlist
