from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton

from gridsync.bridge import get_local_network_ip
from gridsync.gui.qrcode import QRCode


class LinkDeviceDialog(QDialog):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self.qrcode_label = QLabel()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)

        layout = QGridLayout(self)
        layout.addWidget(self.qrcode_label)
        layout.addWidget(self.close_button)

    def go(self):
        lan_ip = get_local_network_ip()
        data = f"{self.gateway.bridge.address} {self.gateway.rootcap}"  # XXX
        # TODO: Create device-specific rootcap
        self.qrcode_label.setPixmap(QPixmap(QRCode(data).scaled(400, 400)))
