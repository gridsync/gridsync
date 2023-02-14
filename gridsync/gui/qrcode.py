from io import BytesIO

import segno
from PyQt5.QtGui import QImage


class QRCode(QImage):
    def __init__(self, data: str) -> None:
        super().__init__()
        buffer = BytesIO()
        segno.make_qr(data).save(buffer, kind="png")
        buffer.seek(0)
        self.loadFromData(buffer.read())
