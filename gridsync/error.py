# -*- coding: utf-8 -*-

from __future__ import print_function

import logging
import sys
import traceback

from PyQt5.QtWidgets import QMessageBox


def error(text, informative_text='', show_message_box=True):
    logging.error(text + str(informative_text))
    print(text, informative_text, file=sys.stderr)
    if show_message_box:
        msg = QMessageBox(QMessageBox.Critical, 'Gridsync - Error', text)
        msg.setInformativeText(informative_text)
        if sys.exc_info()[0]:
            msg.setDetailedText(traceback.format_exc())
        msg.show()
        msg.raise_()
        msg.exec_()
