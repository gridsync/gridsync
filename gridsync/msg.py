# -*- coding: utf-8 -*-

import logging
import sys
from typing import Optional

from qtpy.QtWidgets import QMessageBox, QWidget


def _msgbox(
    parent: Optional[QWidget], title: str, text: str, detailed_text: str = ""
) -> QMessageBox:
    msgbox = QMessageBox(parent)
    if sys.platform == "darwin":
        # Window titles are ignored for macOS "Alerts"; use setText() instead.
        # See https://doc.qt.io/qt-5/qmessagebox.html#the-property-based-api
        msgbox.setText(title)
        msgbox.setInformativeText(text)
    else:
        msgbox.setWindowTitle(title)
        msgbox.setText(text)
    msgbox.setDetailedText(detailed_text)
    return msgbox


def info(
    parent: Optional[QWidget], title: str, text: str, detailed_text: str = ""
) -> int:
    logging.info("%s: %s %s", title, text, detailed_text)
    msgbox = _msgbox(parent, title, text)
    msgbox.setIcon(QMessageBox.Information)
    return msgbox.exec_()


def question(parent: Optional[QWidget], title: str, text: str) -> bool:
    msgbox = _msgbox(parent, title, text)
    msgbox.setIcon(QMessageBox.Question)
    msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msgbox.setDefaultButton(QMessageBox.Yes)
    if msgbox.exec_() == QMessageBox.Yes:
        return True
    return False


def error(
    parent: Optional[QWidget], title: str, text: str, detailed_text: str = ""
) -> int:
    logging.error("%s: %s %s", title, text, detailed_text)
    msgbox = _msgbox(parent, title, text, detailed_text)
    msgbox.setIcon(QMessageBox.Critical)
    return msgbox.exec_()


def critical(title: str, text: str, detailed_text: str = "") -> None:
    logging.critical("%s: %s %s", title, text, detailed_text)
    msgbox = _msgbox(None, title, text, detailed_text)
    msgbox.setIcon(QMessageBox.Critical)
    msgbox.exec_()
    # TODO: Stop reactor?
