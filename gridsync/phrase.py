from mnemonic import Mnemonic


def to_mnemonic(b: bytes, language: str = "english") -> list[str]:
    delimiter = "\u3000" if language.lower() == "japanese" else " " 
    return Mnemonic(language=language).to_mnemonic(b).split(delimiter)


def to_entropy(mnemonic: list[str], language: str = "english") -> bytes:
    return bytes(Mnemonic(language=language).to_entropy(mnemonic))


wordlist = Mnemonic(language="english").wordlist
