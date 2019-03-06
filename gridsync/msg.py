# -*- coding: utf-8 -*-

import logging
import sys

from PyQt5.QtWidgets import QMessageBox


def critical(title, text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    logging.critical(text)
    return msg.exec_()


def error(parent, title, text, detailed_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    if sys.platform == 'darwin':
        # Window titles are ignored for macOS "Alerts"; use setText() instead.
        # See https://doc.qt.io/qt-5/qmessagebox.html#the-property-based-api
        msg.setText(title)
        msg.setInformativeText(text)
    else:
        msg.setWindowTitle(title)
        msg.setText(text)
    msg.setDetailedText(detailed_text)
    logging.error("%s: %s", title, text)
    return msg.exec_()


def info(parent, title, text):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    logging.info(text)
    return msg.exec_()
