import logging
import os
from base64 import b64encode
from typing import List

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableView,
    QWidget,
)

from gridsync import resource
from gridsync.gui.font import Font
from gridsync.gui.qrcode import QRCode
from gridsync.tahoe import Tahoe
from gridsync.util import b58encode


class LinkDeviceDialog(QDialog):
    def __init__(self, gateway: Tahoe) -> None:
        super().__init__()
        self.gateway = gateway

        self.setMinimumSize(QSize(600, 600))

        self.title_label = QLabel("Link Device")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(Font(16))

        self.qrcode_label = QLabel("Please wait; creating link...")
        self.qrcode_label.setAlignment(Qt.AlignCenter)

        self.instructions_label = QLabel("Please wait; creating link...")
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.instructions_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.instructions_label.setWordWrap(True)
        self.instructions_label.hide()

        self.close_button = QPushButton("Close")
        self.close_button.setMaximumWidth(200)
        self.close_button.clicked.connect(self.close)

        layout = QGridLayout(self)
        layout.addWidget(self.title_label, 1, 1)
        layout.addWidget(self.qrcode_label, 2, 1)
        layout.addWidget(self.instructions_label, 3, 1)
        layout.addWidget(self.close_button, 4, 1, Qt.AlignCenter)

    def load_qr_code(self, device_rootcap: str) -> None:
        fp = b64encode(self.gateway.bridge.get_certificate_digest()).decode()
        data = f"{self.gateway.bridge.address} {device_rootcap} {fp}"
        self.qrcode_label.setPixmap(QPixmap(QRCode(data).scaled(400, 400)))
        self.instructions_label.setText(
            "Scan the above QR code with the Tahoe-LAFS mobile\n"
            "application to link it with this device."
        )
        self.instructions_label.show()
        logging.debug("QR code displayed with encoded data: %s", data)  # XXX

    def go(self) -> None:
        device_name = "Device-" + b58encode(os.urandom(8))
        folders = list(self.gateway.magic_folders)
        d = self.gateway.devices_manager.add_new_device(device_name, folders)
        d.addCallback(self.load_qr_code)


class DevicesModel(QStandardItemModel):
    def __init__(self, gateway: Tahoe) -> None:
        super().__init__(0, 2)
        self.gateway = gateway

        self.setHeaderData(0, Qt.Horizontal, "Device Name")
        self.setHeaderData(1, Qt.Horizontal, "Linked Folders")

    def add_device(self, name: str, folders: List[str]) -> None:
        name_item = QStandardItem(QIcon(resource("laptop.png")), name)
        folders_item = QStandardItem(", ".join(sorted(folders)))
        self.appendRow([name_item, folders_item])

    def remove_device(self, name: str) -> None:
        items = self.findItems(name, Qt.MatchExactly, 0)
        if items:
            self.removeRow(items[0].row())


class DevicesTableView(QTableView):
    def __init__(self, gateway: Tahoe) -> None:
        super().__init__()
        self.gateway = gateway

        self._model = DevicesModel(gateway)

        self.setModel(self._model)

        self.setColumnWidth(0, 200)
        self.setShowGrid(False)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setSelectionMode(QTableView.ExtendedSelection)

        vertical_header = self.verticalHeader()
        vertical_header.hide()

        horizontal_header = self.horizontalHeader()
        horizontal_header.setHighlightSections(False)
        horizontal_header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        horizontal_header.setStretchLastSection(True)

        # XXX
        self._model.add_device("one", ["a", "b"])
        self._model.add_device("two", ["a", "c", "b"])

        self._model.remove_device("two")
        self._model.remove_device("three")


class DevicesView(QWidget):
    def __init__(self, gateway: Tahoe):
        super().__init__()
        self.gateway = gateway

        self.link_device_dialog: LinkDeviceDialog = None

        self.table_view = DevicesTableView(gateway)

        self.link_device_button = QPushButton("Link Device...")
        self.link_device_button.setStyleSheet(
            "background: green; color: white"
        )
        self.link_device_button.setFixedSize(150, 32)
        self.link_device_button.clicked.connect(
            self.on_link_device_button_clicked
        )

        layout = QGridLayout(self)
        layout.addWidget(self.link_device_button)
        layout.addWidget(self.table_view)

    def on_link_device_button_clicked(self) -> None:
        self.link_device_dialog = LinkDeviceDialog(self.gateway)
        self.link_device_dialog.show()
        self.link_device_dialog.go()
