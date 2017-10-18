# -*- coding: utf-8 -*-

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import (
    QAction, QGridLayout, QLabel, QLineEdit, QProgressBar, QSizePolicy,
    QSpacerItem, QWidget)
from zxcvbn import zxcvbn

from gridsync import resource


class PasswordLineEdit(QLineEdit):
    def __init__(self):
        super(PasswordLineEdit, self).__init__()
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        self.setEchoMode(QLineEdit.Password)
        self.action = QAction(
            QIcon(resource('eye.png')), "Toggle visibility", self)
        self.addAction(self.action, QLineEdit.TrailingPosition)
        self.action.triggered.connect(self.toggle_visibility)

    def toggle_visibility(self, _):
        if self.echoMode() == QLineEdit.Password:
            self.setEchoMode(QLineEdit.Normal)
        else:
            self.setEchoMode(QLineEdit.Password)


class PasswordCreationWidget(QWidget):

    done = pyqtSignal(str)

    def __init__(self):
        super(PasswordCreationWidget, self).__init__()
        self.setMinimumSize(400, 200)

        self.password_label = QLabel("Password:")
        font = QFont()
        font.setPointSize(14)
        self.password_label.setFont(font)
        self.password_label.setStyleSheet('color: gray')

        self.password_field = PasswordLineEdit()

        self.progressbar = QProgressBar()
        self.progressbar.setMaximum(4)
        self.progressbar.setTextVisible(False)
        self.progressbar.setFixedHeight(5)
        self.progressbar.setStyleSheet(
            'QProgressBar { background-color: transparent }'
            'QProgressBar::chunk { background-color: gray }'
        )

        self.rating_label = QLabel()
        self.rating_label.setAlignment(Qt.AlignRight)

        self.time_label = QLabel()
        self.time_label.setStyleSheet('color: gray')

        self.warning_label = QLabel()
        self.warning_label.setAlignment(Qt.AlignCenter)
        self.warning_label.setWordWrap(True)

        layout = QGridLayout(self)
        layout.addWidget(self.password_label, 1, 1)
        layout.addWidget(self.password_field, 2, 1)
        layout.addWidget(self.progressbar, 3, 1)
        layout.addWidget(self.time_label, 4, 1)
        layout.addWidget(self.rating_label, 4, 1)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 6, 1)
        layout.addWidget(self.warning_label, 7, 1)
        layout.addItem(QSpacerItem(0, 0, 0, QSizePolicy.Expanding), 8, 1)

        self.password_field.textChanged.connect(self.update_stats)
        self.password_field.returnPressed.connect(self.on_return_pressed)

        self.update_color('transparent')

    def update_color(self, color):
        self.rating_label.setStyleSheet('color: {}'.format(color))
        self.progressbar.setStyleSheet(
            'QProgressBar {{ background-color: transparent }}'
            'QProgressBar::chunk {{ background-color: {} }}'.format(color))

    def update_stats(self, text):
        if not text:
            self.time_label.setText('')
            self.warning_label.setText('')
            self.rating_label.setText('')
            self.progressbar.setValue(0)
            return
        res = zxcvbn(text)
        t = res['crack_times_display']['offline_slow_hashing_1e4_per_second']
        self.time_label.setText("Time to crack: {}".format(t))
        s = res['crack_times_seconds']['offline_slow_hashing_1e4_per_second']
        seconds = int(s)
        if seconds == 0:
            self.rating_label.setText("Very weak")
            self.update_color('lightgray')
            self.rating_label.setStyleSheet('color: gray')
            self.progressbar.setValue(1)
        elif seconds < 86400:  # 1 day
            self.rating_label.setText("Weak")
            self.update_color('red')
            self.progressbar.setValue(1)
        elif seconds < 2592000:  # 1 month
            self.rating_label.setText("Alright")
            self.update_color('orange')
            self.progressbar.setValue(2)
        elif seconds < 3153600000:  # 100 years
            self.rating_label.setText("Good")
            self.update_color('#9CC259')
            self.progressbar.setValue(3)
        else:  # > 100 years
            self.rating_label.setText("Excellent")
            self.update_color('#00B400')
            self.progressbar.setValue(4)
        warning = res['feedback']['warning']
        if warning:
            self.rating_label.setToolTip(warning)
            self.password_field.setToolTip(warning)
            self.warning_label.setText(warning)

    def reset(self):
        self.password_field.setText(None)
        self.update_stats(None)

    def on_return_pressed(self):
        self.done.emit(self.password_field.text())
        self.close()
        self.reset()
