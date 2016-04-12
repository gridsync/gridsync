# -*- coding: utf-8 -*-

import logging

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLineEdit, QPushButton, QVBoxLayout)


class NewFolderWindow(QDialog):
    def __init__(self, parent):
        super(NewFolderWindow, self).__init__()
        self.parent = parent
        self.setWindowTitle("Gridsync - Add New Sync Folder")
        self.resize(500, 225)
        self.layout = QVBoxLayout(self)

        layout = QVBoxLayout()

        grid_group_box = QGroupBox(self)
        grid_group_box.setTitle("Select remote storage grid to use:")
        grid_layout = QHBoxLayout(grid_group_box)
        self.grid_combo_box = QComboBox(grid_group_box)
        self.populate_combo_box()
        grid_layout.addWidget(self.grid_combo_box)
        layout.addWidget(grid_group_box)

        folder_group_box = QGroupBox(self)
        folder_group_box.setTitle("Select local folder to sync:")
        folder_layout = QHBoxLayout(folder_group_box)
        self.folder_text = QLineEdit(folder_group_box)
        folder_layout.addWidget(self.folder_text)
        folder_button = QPushButton(folder_group_box)
        folder_button.setText("Browse...")
        folder_button.clicked.connect(self.get_folder)
        folder_layout.addWidget(folder_button)
        layout.addWidget(folder_group_box)

        self.layout.addLayout(layout)

        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.rejected.connect(self.close)
        button_box.accepted.connect(self.create_new_folder)
        self.layout.addWidget(button_box)

    def populate_combo_box(self):
        logging.debug("(Re-)populating combo box...")
        self.grid_combo_box.clear()
        for gateway in self.parent.gateways:
            self.grid_combo_box.addItem(gateway.location, gateway)
        self.grid_combo_box.insertSeparator(len(self.parent.gateways))
        self.grid_combo_box.addItem("Add New Grid...")
        #self.grid_combo_box.setEnabled(False)

    def get_folder(self):
        self.folder = QFileDialog.getExistingDirectory(
            self, "Select local folder to sync")
        if self.folder:
            self.folder_text.setText(self.folder)

    def create_new_folder(self):
        if self.folder_text.text() and self.grid_combo_box.currentText():
            self.close()
            selected_folder = str(self.folder_text.text())
            selected_grid = str(self.grid_combo_box.currentText())
            for gateway in self.parent.gateways:
                if gateway.name == selected_grid:
                    tahoe = gateway
            tahoe.add_sync_folder(selected_folder)
