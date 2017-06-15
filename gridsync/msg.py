# -*- coding: utf-8 -*-

import logging

from PyQt5.QtWidgets import QMessageBox


def critical(title, text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    logging.critical(text)
    return msg.exec_()
