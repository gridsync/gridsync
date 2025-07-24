# type: ignore
# TODO: Type hints
import secrets

from mnemonic import Mnemonic
from qtpy.QtCore import QStringListModel, Qt, Signal
from qtpy.QtGui import QKeyEvent
from qtpy.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QWidget,
)

from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.widgets import HSpacer, VSpacer
from gridsync.msg import error

SUPPORTED_LANGUAGES = Mnemonic.list_languages()


def generate_recovery_phrase(language: str = "english") -> list[str]:
    return Mnemonic(language.lower()).generate(128).split(" ")


def generate_entropy(strength: int = 128) -> bytes:
    return secrets.token_bytes(strength // 8)


def detect_language(phrase: str) -> str:
    return Mnemonic.detect_language(phrase)


def get_wordlist(language: str = "english") -> list[str]:
    lang = language.lower()
    if lang not in Mnemonic.list_languages():
        raise ValueError(f"Invalid language: {lang}")
    return Mnemonic(language=lang).wordlist


def to_bytes(phrase: str) -> bytes:
    language = Mnemonic.detect_language(phrase)
    return bytes(Mnemonic(language=language).to_entropy(phrase))


class LanguageSelector(QComboBox):
    language_changed = Signal(str)
    language_codes = {
        # from mnemonic.Mnemonic.list_languages()
        "chinese_simplified": "zh_Hans",
        "chinese_traditional": "zh_Hant",
        "czech": "cs",
        "english": "en",
        "french": "fr",
        "italian": "it",
        "japanese": "ja",
        "korean": "ko",
        "portuguese": "pt",
        "russian": "ru",
        "spanish": "es",
        "turkish": "tr",
    }

    def __init__(
        self, language: str = "english", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        # Sort by language code:
        codes = dict(sorted(self.language_codes.items(), key=lambda x: x[1]))
        for name, code in codes.items():
            # Display the shorthand language code in the combo box;
            # store the full language name in the item's UserRole slot.
            self.addItem(code, name)

        self.set_language(language)

        self.currentIndexChanged.connect(
            lambda i: self.language_changed.emit(self.itemData(i, Qt.UserRole))
        )

    def set_language(self, language: str) -> None:
        self.setCurrentIndex(self.findData(language, Qt.UserRole))


class RecoveryPhraseCompleter(QCompleter):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.InlineCompletion)

        self._model = QStringListModel([], self)
        self._model.setStringList(get_wordlist())
        self.setModel(self._model)

    def set_language(self, language: str) -> None:
        print(self._model.setStringList(get_wordlist(language)))


class RecoveryPhraseGroupBox(QGroupBox):
    def __init__(
        self,
        title: str | None,
        read_only: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QGroupBox {font-size: 18px}")
        self.setTitle(title)

        self._entropy = b""
        self._language = ""
        self._line_edits = {}

        self.completer = RecoveryPhraseCompleter(self)
        self.layout = QGridLayout(self)

        p = self.palette()
        grey = BlendedColor(p.windowText().color(), p.window().color()).name()

        # Create 12 labels in 2 column, 6 row grid layout:
        for i in range(1, 13):  # For a phrase length of 12
            label = QLabel(str(i) + ".")
            label.setStyleSheet("color: {}".format(grey))
            label.setFont(Font(16))
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            le = QLineEdit("", parent=self)
            le.setReadOnly(read_only)
            le.setFont(Font(16))
            le.setCompleter(self.completer)

            if i & 1:  # odd; place in left column
                column = (i + 1) // 2
                self.layout.addWidget(label, column, 1)
                self.layout.addWidget(le, column, 2)
            else:  # even; place in right column
                column = i // 2
                self.layout.addWidget(label, column, 3)
                self.layout.addWidget(le, column, 4)

            # Store the line edit objects in a dictionary for later access:
            self._line_edits[i] = le

    def load(self, entropy: bytes, language: str = "english") -> None:
        print("load", entropy, language)
        if not entropy:
            raise ValueError("Entropy must be non-empty")
        self._entropy = entropy

        # Japanese must be joined by ideographic space
        delimiter = "\u3000" if language == "japanese" else " "
        phrase = (
            Mnemonic(language=language).to_mnemonic(entropy).split(delimiter)
        )
        for i, word in enumerate(phrase, 1):
            self._line_edits[i].setText(word)

        self._language = language
        self.completer.set_language(language)

    def get_phrase(self) -> str:
        return " ".join([self._line_edits[i].text() for i in range(1, 13)])

    def get_entropy(self) -> bytes:
        return to_bytes(self.get_phrase())


class RecoveryPhraseExporter(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entropy = b""

        self._recovery_box = RecoveryPhraseGroupBox(
            "Recovery Phrase:", read_only=True, parent=self
        )
        self._language_selector = LanguageSelector()

        self._layout = QGridLayout(self)
        self._layout.addItem(VSpacer(), 0, 0)
        self._layout.addItem(HSpacer(), 0, 0)
        self._layout.addWidget(self._recovery_box, 1, 1, 1, 5)
        self._layout.addWidget(self._language_selector, 20, 1, 1, 1)
        self._layout.addItem(HSpacer(), 99, 99)
        self._layout.addItem(VSpacer(), 99, 99)

        self._language_selector.language_changed.connect(
            lambda language: self.load(self._entropy, language)
        )

    def load(self, entropy: bytes, language: str = "english") -> None:
        self._entropy = entropy
        self._recovery_box.load(entropy, language)


class RecoveryPhraseImporter(QDialog):
    completed = Signal(bytes)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entropy = b""
        self._language = ""

        self._recovery_box = RecoveryPhraseGroupBox(
            "Enter your Recovery Phrase:", read_only=False, parent=self
        )
        self._language_selector = LanguageSelector()

        self._layout = QGridLayout(self)
        self._layout.addItem(VSpacer(), 0, 0)
        self._layout.addItem(HSpacer(), 0, 0)
        self._layout.addWidget(self._recovery_box, 1, 1, 1, 5)
        self._layout.addWidget(self._language_selector, 20, 1, 1, 1)
        self._layout.addItem(HSpacer(), 99, 99)
        self._layout.addItem(VSpacer(), 99, 99)

        self._language_selector.language_changed.connect(
            lambda language: self.load(self._entropy, language)
        )

    def load(self, entropy: bytes, language: str = "english") -> None:
        self._entropy = entropy
        self._language = language
        self._recovery_box.load(entropy, language)

    def validate(self) -> None:
        try:
            entropy = self._recovery_box.get_entropy()
        except Exception as e:  # pylint: disable=broad-except
            error(
                self,
                "Invalid Recovery Phrase",
                f"The Recovery Phrase you entered is invalid: {e}\n\n"
                "Please verify that each word was entered correctly and "
                "try again.",
            )
            return
        self.completed.emit(entropy)

    def keyPressEvent(self, event: QKeyEvent) -> QKeyEvent | None:
        key = event.key()
        if key == Qt.Key_Return:
            self.validate()
            return None
        else:
            return QDialog.keyPressEvent(self, event)
