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


def error(parent, title, text, detailed_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setDetailedText(detailed_text)
    logging.error(text)
    return msg.exec_()
