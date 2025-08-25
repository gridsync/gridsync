from mnemonic import Mnemonic

from gridsync.gui.phrase import LanguageSelector


def test_selector_languages_have_wordlist() -> None:
    supported_languages = Mnemonic.list_languages()
    for language in LanguageSelector.language_codes:
        assert language in supported_languages


# def test_supported_languages_in_selector() -> None:
#     supported_languages = Mnemonic.list_languages()
