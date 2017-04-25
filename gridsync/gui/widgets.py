# -*- coding: utf-8 -*-

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QDialogButtonBox, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout, QWidget)

from gridsync import resource
from gridsync.config import Config
from gridsync.tahoe import is_valid_furl


class ConnectionSettings(QWidget):
    def __init__(self):
        super(ConnectionSettings, self).__init__()

        self.name_label = QLabel("Name:")
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


class EncodingParameters(QWidget):
    def __init__(self):
        super(EncodingParameters, self).__init__()

        self.total_label = QLabel("shares.total (N)")
        self.total_spinbox = QSpinBox()
        self.total_spinbox.setMinimum(1)

        self.needed_label = QLabel("shares.needed (K)")
        self.needed_spinbox = QSpinBox()
        self.needed_spinbox.setMinimum(1)

        self.happy_label = QLabel("shares.happy (H)")
        self.happy_spinbox = QSpinBox()
        self.happy_spinbox.setMinimum(1)

        layout = QGridLayout(self)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, 0), 1, 1, 1, 4)
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
        super(TahoeConfigForm, self).__init__()

        self.connection_settings = ConnectionSettings()
        self.encoding_parameters = EncodingParameters()

        connection_settings_gbox = QGroupBox(self)
        connection_settings_gbox.setTitle("Connection settings:")
        connection_settings_gbox_layout = QVBoxLayout(connection_settings_gbox)
        connection_settings_gbox_layout.addWidget(self.connection_settings)

        encoding_parameters_gbox = QGroupBox(self)
        encoding_parameters_gbox.setTitle("Encoding parameters:")
        encoding_parameters_gbox_layout = QVBoxLayout(encoding_parameters_gbox)
        encoding_parameters_gbox_layout.addWidget(self.encoding_parameters)

        self.buttonbox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        layout = QGridLayout(self)
        layout.addWidget(connection_settings_gbox)
        layout.addWidget(encoding_parameters_gbox)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        layout.addWidget(self.buttonbox)

    def reset(self):
        self.connection_settings.name_line_edit.setText('')
        self.connection_settings.introducer_text_edit.setPlainText('')
        self.encoding_parameters.total_spinbox.setValue(1)
        self.encoding_parameters.needed_spinbox.setValue(1)
        self.encoding_parameters.happy_spinbox.setValue(1)

    def get_settings(self):
        furl = self.connection_settings.introducer_text_edit.toPlainText()
        return {
            'nickname': self.connection_settings.name_line_edit.text().strip(),
            'introducer': furl.lower().strip(),
            'shares-total': self.encoding_parameters.total_spinbox.value(),
            'shares-needed': self.encoding_parameters.needed_spinbox.value(),
            'shares-happy': self.encoding_parameters.happy_spinbox.value()
        }


class GridComboBox(QWidget):
    def __init__(self):
        super(GridComboBox, self).__init__()

        #self.label = QLabel('Storage provider:')
        #self.label.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, 0))

        self.combo_box = QComboBox(self)

        hbox = QHBoxLayout(self)
        hbox.addItem(QSpacerItem(100, 0, QSizePolicy.Preferred, 0))
        #hbox.addWidget(self.label)
        hbox.addWidget(self.combo_box)
        hbox.addItem(QSpacerItem(100, 0, QSizePolicy.Preferred, 0))


class GridDescription(QWidget):
    def __init__(self):
        super(GridDescription, self).__init__()

        self.image = QLabel()

        self.description = QLabel('', self)
        self.description.setWordWrap(True)
        self.description.setOpenExternalLinks(True)

        form = QFormLayout()
        form.setWidget(0, QFormLayout.LabelRole, self.image)
        form.setWidget(0, QFormLayout.FieldRole, self.description)

        hbox = QHBoxLayout(self)
        hbox.addItem(QSpacerItem(30, 0, QSizePolicy.Preferred, 0))
        hbox.addLayout(form)
        hbox.addItem(QSpacerItem(30, 0, QSizePolicy.Preferred, 0))


class GridForm(QWidget):
    def __init__(self):
        super(GridForm, self).__init__()

        self.name_label = QLabel("Name (optional):")

        self.name_line_edit = QLineEdit()

        self.introducer_label = QLabel("Introducer fURL:")

        self.introducer_text_edit = QPlainTextEdit()
        self.introducer_text_edit.setMaximumHeight(70)
        self.introducer_text_edit.setTabChangesFocus(True)

        self.description_label = QLabel("Description (optional):")

        self.description_text_edit = QPlainTextEdit()
        self.description_text_edit.setMaximumHeight(70)
        self.description_text_edit.setTabChangesFocus(True)

        self.push_button = QPushButton("Save")

        form = QFormLayout()
        form.setWidget(0, QFormLayout.LabelRole, self.name_label)
        form.setWidget(0, QFormLayout.FieldRole, self.name_line_edit)
        form.setWidget(1, QFormLayout.LabelRole, self.introducer_label)
        form.setWidget(1, QFormLayout.FieldRole, self.introducer_text_edit)
        #form.setWidget(2, QFormLayout.LabelRole, self.description_label)
        #form.setWidget(2, QFormLayout.FieldRole, self.description_text_edit)
        form.setWidget(3, QFormLayout.FieldRole, self.push_button)

        hbox = QHBoxLayout(self)
        #hbox.addItem(QSpacerItem(100, 0, QSizePolicy.Preferred, 0))
        hbox.addLayout(form)
        #hbox.addItem(QSpacerItem(100, 0, QSizePolicy.Preferred, 0))


class GridSelector(QWidget):
    def __init__(self):
        super(GridSelector, self).__init__()
        self.resize(800, 500)
        self.introducer_furl = None
        self.storage_providers = None

        self.grid_combo_box = GridComboBox()
        self.grid_combo_box.combo_box.activated[str].connect(self.on_selected)

        self.grid_description = GridDescription()
        self.grid_description.hide()

        self.grid_form = GridForm()
        self.grid_form.push_button.clicked.connect(self.on_save)
        self.grid_form.hide()

        gbox = QGroupBox(self)
        gbox.setTitle("Select a storage grid:")
        gbox_layout = QVBoxLayout(gbox)
        gbox_layout.addWidget(self.grid_combo_box)
        gbox_layout.addWidget(self.grid_description)
        gbox_layout.addWidget(self.grid_form)
        #gbox_layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))

        vbox = QVBoxLayout(self)
        #vbox.addItem(QSpacerItem(0, 60, 0, QSizePolicy.Minimum))
        #vbox.addWidget(self.grid_selector)
        #vbox.addWidget(self.grid_description)
        #vbox.addWidget(self.new_grid_form)
        #vbox.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding))
        vbox.addWidget(gbox)

        self.combo_box = self.grid_combo_box.combo_box
        self.image = self.grid_description.image
        self.description = self.grid_description.description

        self.populate_combo_box()

    def populate_combo_box(self):
        self.storage_providers = Config(
            resource('storage_providers.txt')).load()
        self.combo_box.clear()
        self.combo_box.addItem(" ")
        for name in sorted(self.storage_providers.keys(), reverse=True):
            self.combo_box.addItem(name)
        self.combo_box.insertSeparator(
            self.combo_box.count())
        self.combo_box.addItem("Add new...")

    def on_selected(self, name):
        if self.combo_box.itemText(0) == " ":
            self.combo_box.removeItem(0)
        if name == " ":
            return
        elif name == "Add new...":
            self.grid_description.hide()
            self.grid_form.show()
        else:
            provider = self.storage_providers[name]
            self.introducer_furl = provider['introducer']
            description = provider['description']
            try:
                description += '<p>Homepage: <a href="{}">{}</a>'.format(
                    provider['homepage'], provider['homepage'])
            except KeyError:
                pass
            self.description.setText(description)
            try:
                pixmap = QPixmap(resource(provider['icon'])).scaled(64, 64)
                self.image.setPixmap(pixmap)
                self.image.show()
            except KeyError:
                self.image.hide()
            self.grid_form.hide()
            self.grid_description.show()

    def on_save(self):
        introducer_furl = self.grid_form.introducer_text_edit.toPlainText()
        introducer_furl = introducer_furl.lower().strip().strip('"').strip("'")
        #name = self.grid_form.name_line_edit.text()
        if not introducer_furl:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Gridsync")
            msg.setText("Please enter an Introducer fURL.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        elif is_valid_furl(introducer_furl):
            self.introducer_furl = introducer_furl
        else:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Gridsync")
            msg.setText("Please enter a valid Introducer fURL.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
