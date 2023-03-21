from io import BytesIO

import segno
from qtpy.QtGui import QImage


class QRCode(QImage):
    def __init__(self, data: str) -> None:
        super().__init__()
        buffer = BytesIO()
        segno.make_qr(data).save(buffer, kind="png", border=1)
        buffer.seek(0)
        self.loadFromData(buffer.read())
