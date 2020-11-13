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


# XXX
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QGridLayout, QLabel, QWidget
    from PyQt5.QtGui import QPixmap
    app = QApplication(sys.argv)
    w = QWidget()
    layout = QGridLayout(w)
    label = QLabel()
    label.setPixmap(QPixmap(QRCode("TEST").scaled(256, 256)))
    layout.addWidget(label)
    w.show()
    sys.exit(app.exec_())
