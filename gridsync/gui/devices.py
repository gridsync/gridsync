import logging
import os
from base64 import b64encode

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QWidget

from gridsync.gui.font import Font
from gridsync.gui.qrcode import QRCode
from gridsync.util import b58encode


class LinkDeviceDialog(QDialog):
    def __init__(self, gateway):
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


class DevicesView(QWidget):
    def __init__(self, gateway, gui):
        super().__init__()
        self.gateway = gateway
        self.gui = gui

        self.link_device_dialog = None

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

    def on_link_device_button_clicked(self):
        self.link_device_dialog = LinkDeviceDialog(self.gateway)
        self.link_device_dialog.show()
        self.link_device_dialog.go()
