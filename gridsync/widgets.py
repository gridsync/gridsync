# -*- coding: utf-8 -*-

import sys

from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from gridsync.providers import get_storage_providers, add_storage_provider
from gridsync.tahoe import decode_introducer_furl
from gridsync import resources


class GridSelector(QWidget):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.layout = QHBoxLayout(self)

        left_spacer = QSpacerItem(
                100, 0, QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.layout.addItem(left_spacer)

        self.label = QLabel('Storage provider:')
        self.label.setSizePolicy(
                QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred))
        self.layout.addWidget(self.label)

        self.combo_box = QComboBox(self)
        self.storage_providers = get_storage_providers()
        self.combo_box.addItem("--")
        for name in sorted(self.storage_providers.keys(), reverse=True):
            self.combo_box.addItem(name)
        self.combo_box.insertSeparator(self.combo_box.count())
        self.combo_box.addItem("Add new...")
        self.layout.addWidget(self.combo_box)

        right_spacer = QSpacerItem(
                100, 0, QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.layout.addItem(right_spacer)


class GridDescription(QWidget):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.layout = QFormLayout(self)

        self.image_box = QLabel()
        self.layout.setWidget(0, QFormLayout.LabelRole, self.image_box)

        self.label = QLabel('', self)
        self.label.setWordWrap(True)
        self.label.setText('')
        self.label.setOpenExternalLinks(True)
        self.layout.setWidget(0, QFormLayout.FieldRole, self.label)

        self.image_box.hide()
        self.label.linkActivated.connect(self.clicked)

    def clicked(self, link):
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(link))

class NewGridForm(QWidget):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.layout = QFormLayout(self)

        self.name_label = QLabel("Name (optional):")
        self.layout.setWidget(0, QFormLayout.LabelRole, self.name_label)

        self.name_line_edit = QLineEdit()
        self.layout.setWidget(0, QFormLayout.FieldRole, self.name_line_edit)

        self.introducer_label = QLabel("Introducer fURL:")
        self.layout.setWidget(
                1, QFormLayout.LabelRole, self.introducer_label)

        self.introducer_text_edit = QPlainTextEdit()
        self.layout.setWidget(
                1, QFormLayout.FieldRole, self.introducer_text_edit)
        self.introducer_text_edit.setMaximumHeight(70)
        self.introducer_text_edit.setTabChangesFocus(True)

        #self.description_label = QLabel("Description (optional):")
        #self.layout.setWidget(
        #        2, QFormLayout.LabelRole, self.description_label)

        #self.description_text_edit = QPlainTextEdit()
        #self.layout.setWidget(
        #        2, QFormLayout.FieldRole, self.description_text_edit)
        #self.description_text_edit.setMaximumHeight(70)
        #self.description_text_edit.setTabChangesFocus(True)

        self.push_button = QPushButton("Save")
        self.layout.setWidget(3, QFormLayout.FieldRole, self.push_button)


class StorageProviderSelector(QWidget):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.layout = QVBoxLayout(self)
        self.resize(800, 500)

        self.grid_selector = GridSelector()
        self.layout.addWidget(self.grid_selector)

        self.grid_description = GridDescription()
        self.layout.addWidget(self.grid_description)

        self.new_grid_form = NewGridForm()
        self.layout.addWidget(self.new_grid_form)

        self.spacer = QSpacerItem(
                1, 0, QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.layout.addItem(self.spacer)

        self.new_grid_form.hide()
        self.grid_selector.combo_box.activated[str].connect(self.on_selected)
        self.new_grid_form.push_button.clicked.connect(self.on_save)

    def on_selected(self, name):
        if name == "Add new...":
            self.grid_description.hide()
            self.new_grid_form.show()
        else:
            if self.grid_selector.combo_box.itemText(0) == "--":
                self.grid_selector.combo_box.removeItem(0)
            provider = self.grid_selector.storage_providers[name]
            description = provider['description']
            try:
                description += '<p>Homepage: <a href="{}">{}</a>'.format(
                        provider['homepage'], provider['homepage'])
            except KeyError:
                pass
            self.grid_description.label.setText(description)
            try:
                pixmap = QPixmap(provider['logo']).scaled(64, 64)
                self.grid_description.image_box.setPixmap(pixmap)
                self.grid_description.image_box.show()
            except KeyError:
                self.grid_description.image_box.hide()
            self.new_grid_form.hide()
            self.grid_description.show()
    
    def on_save(self):
        introducer_furl = self.new_grid_form.introducer_text_edit.toPlainText()
        #name = self.new_grid_form.name_line_edit.text()
        #description = self.new_grid_form.description_text_edit.toPlainText()
        if not introducer_furl:
            # TODO: QMessageBox
            print('no introducer')
        try:
            _, connection_hints = decode_introducer_furl(introducer_furl)
        except AttributeError:
            # TODO: QMessageBox
            print('invalid furl')
        #print(introducer_furl)
        #print(name)
        #print(description)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = StorageProviderSelector()
    win.show()
    sys.exit(app.exec_())
