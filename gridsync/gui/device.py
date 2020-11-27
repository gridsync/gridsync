from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton

from gridsync.gui.font import Font
from gridsync.gui.qrcode import QRCode


class LinkDeviceDialog(QDialog):
    def __init__(self, gateway):
        super().__init__()
        self.gateway = gateway

        self.setMinimumSize(QSize(500, 500))

        self.title_label = QLabel("Link Device")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(Font(16))

        self.qrcode_label = QLabel()
        self.qrcode_label.setAlignment(Qt.AlignCenter)

        self.instructions_label = QLabel(
            "Scan the above QR code with the Tahoe-LAFS mobile\n"
            "application to link it with this device."
        )
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.instructions_label.setWordWrap(True)

        self.close_button = QPushButton("Close")
        self.close_button.setMaximumWidth(200)
        self.close_button.clicked.connect(self.close)

        layout = QGridLayout(self)
        layout.addWidget(self.title_label, 1, 1)
        layout.addWidget(self.qrcode_label, 2, 1)
        layout.addWidget(self.instructions_label, 3, 1)
        layout.addWidget(self.close_button, 4, 1, Qt.AlignCenter)

    def go(self):
        data = f"{self.gateway.bridge.address} {self.gateway.rootcap}"  # XXX
        # TODO: Create device-specific rootcap
        self.qrcode_label.setPixmap(QPixmap(QRCode(data).scaled(400, 400)))
