# -*- coding: utf-8 -*-

from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QComboBox,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QWidget,
)
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from gridsync.tor import get_tor


class VSpacer(QSpacerItem):
    def __init__(self):
        super().__init__(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)


class HSpacer(QSpacerItem):
    def __init__(self):
        super().__init__(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)


class ClickableLabel(QLabel):

    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class ConnectionSettings(QWidget):
    def __init__(self):
        super().__init__()

        self.name_label = QLabel("Grid name:")
        self.name_line_edit = QLineEdit()

        self.introducer_label = QLabel("Introducer fURL:")
        self.introducer_text_edit = QPlainTextEdit()
        self.introducer_text_edit.setMaximumHeight(70)
        self.introducer_text_edit.setTabChangesFocus(True)

        self.mode_label = QLabel("Connection mode:")
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItem("Normal")
        self.mode_combobox.addItem("Tor")
        self.mode_combobox.model().item(1).setEnabled(False)
        self.mode_combobox.addItem("I2P")
        self.mode_combobox.model().item(2).setEnabled(False)

        form = QFormLayout(self)
        form.setWidget(0, QFormLayout.LabelRole, self.name_label)
        form.setWidget(0, QFormLayout.FieldRole, self.name_line_edit)
        form.setWidget(1, QFormLayout.LabelRole, self.introducer_label)
        form.setWidget(1, QFormLayout.FieldRole, self.introducer_text_edit)
        form.setWidget(2, QFormLayout.LabelRole, self.mode_label)
        form.setWidget(2, QFormLayout.FieldRole, self.mode_combobox)

        self.maybe_enable_tor()

    @inlineCallbacks
    def maybe_enable_tor(self):
        tor = yield get_tor(reactor)
        if tor:
            self.mode_combobox.model().item(1).setEnabled(True)


class EncodingParameters(QWidget):
    def __init__(self):
        super().__init__()

        self.total_label = QLabel("shares.total (N)")
        self.total_spinbox = QSpinBox()
        self.total_spinbox.setRange(1, 255)

        self.needed_label = QLabel("shares.needed (K)")
        self.needed_spinbox = QSpinBox()
        self.needed_spinbox.setRange(1, 255)

        self.happy_label = QLabel("shares.happy (H)")
        self.happy_spinbox = QSpinBox()
        self.happy_spinbox.setRange(1, 255)

        layout = QGridLayout(self)
        layout.addItem(HSpacer(), 1, 1, 1, 4)
        layout.addWidget(self.total_label, 1, 2)
        layout.addWidget(self.total_spinbox, 1, 3)
        layout.addWidget(self.needed_label, 2, 2)
        layout.addWidget(self.needed_spinbox, 2, 3)
        layout.addWidget(self.happy_label, 3, 2)
        layout.addWidget(self.happy_spinbox, 3, 3)

        self.needed_spinbox.valueChanged.connect(self.on_value_changed)
        self.happy_spinbox.valueChanged.connect(self.on_value_changed)
        self.total_spinbox.valueChanged.connect(self.on_total_changed)

    def on_value_changed(self, value):
        if value >= self.total_spinbox.value():
            self.total_spinbox.setValue(value)

    def on_total_changed(self, value):
        if value <= self.needed_spinbox.value():
            self.needed_spinbox.setValue(value)
        if value <= self.happy_spinbox.value():
            self.happy_spinbox.setValue(value)


class TahoeConfigForm(QWidget):
    def __init__(self):
        super().__init__()
        self.rootcap = None
        self.settings = {}
        self.progress = None
        self.animation = None
        self.crypter = None
        self.crypter_thread = None

        self.connection_settings = ConnectionSettings()
        self.encoding_parameters = EncodingParameters()

        connection_settings_gbox = QGroupBox(self)
        connection_settings_gbox.setTitle("Connection settings:")
        connection_settings_gbox_layout = QGridLayout(connection_settings_gbox)
        connection_settings_gbox_layout.addWidget(self.connection_settings)

        encoding_parameters_gbox = QGroupBox(self)
        encoding_parameters_gbox.setTitle("Encoding parameters:")
        encoding_parameters_gbox_layout = QGridLayout(encoding_parameters_gbox)
        encoding_parameters_gbox_layout.addWidget(self.encoding_parameters)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )

        layout = QGridLayout(self)
        layout.addWidget(connection_settings_gbox)
        layout.addWidget(encoding_parameters_gbox)
        layout.addItem(VSpacer())
        layout.addWidget(self.buttonbox)

    def set_name(self, name):
        self.connection_settings.name_line_edit.setText(name)

    def set_introducer(self, introducer):
        self.connection_settings.introducer_text_edit.setPlainText(introducer)

    def set_shares_total(self, shares):
        self.encoding_parameters.total_spinbox.setValue(int(shares))

    def set_shares_needed(self, shares):
        self.encoding_parameters.needed_spinbox.setValue(int(shares))

    def set_shares_happy(self, shares):
        self.encoding_parameters.happy_spinbox.setValue(int(shares))

    def get_name(self):
        return self.connection_settings.name_line_edit.text().strip()

    def get_introducer(self):
        furl = self.connection_settings.introducer_text_edit.toPlainText()
        return furl.lower().strip()

    def get_shares_total(self):
        return self.encoding_parameters.total_spinbox.value()

    def get_shares_needed(self):
        return self.encoding_parameters.needed_spinbox.value()

    def get_shares_happy(self):
        return self.encoding_parameters.happy_spinbox.value()

    def reset(self):
        self.set_name("")
        self.set_introducer("")
        self.set_shares_total(1)
        self.set_shares_needed(1)
        self.set_shares_happy(1)
        self.rootcap = None

    def get_settings(self):
        settings = {
            "nickname": self.get_name(),
            "introducer": self.get_introducer(),
            "shares-total": self.get_shares_total(),
            "shares-needed": self.get_shares_needed(),
            "shares-happy": self.get_shares_happy(),
            "rootcap": self.rootcap,  # Maybe this should be user-settable?
        }
        if self.connection_settings.mode_combobox.currentIndex() == 1:
            settings["hide-ip"] = True
        return settings
