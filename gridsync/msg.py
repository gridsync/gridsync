# -*- coding: utf-8 -*-

import sys

from qtpy.QtWidgets import QMessageBox, QWidget


def critical(title, text):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    return msg.exec_()


def error(parent, title, text, detailed_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    if sys.platform == "darwin":
        # Window titles are ignored for macOS "Alerts"; use setText() instead.
        # See https://doc.qt.io/qt-5/qmessagebox.html#the-property-based-api
        msg.setText(title)
        msg.setInformativeText(text)
    else:
        msg.setWindowTitle(title)
        msg.setText(text)
    msg.setDetailedText(detailed_text)
    return msg.exec_()


def question(parent: QWidget, title: str, text: str) -> bool:
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Question)
    if sys.platform == "darwin":
        msg.setText(title)
        msg.setInformativeText(text)
    else:
        msg.setWindowTitle(title)
        msg.setText(text)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes)
    if msg.exec_() == QMessageBox.Yes:
        return True
    return False


def info(parent, title, text):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    return msg.exec_()
