# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QProgressBar,
)
from zxcvbn import zxcvbn

from gridsync import resource
from gridsync.gui.font import Font
from gridsync.gui.widgets import VSpacer

if TYPE_CHECKING:
    from qtpy.QtCore import QEvent
    from qtpy.QtWidgets import QWidget


class PasswordDialog(QDialog):
    def __init__(  # pylint: disable=too-many-arguments
        self,
        label: str = "",
        ok_button_text: str = "",
        help_text: str = "",
        show_stats: bool = True,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setMinimumWidth(400)

        self.label = QLabel("Password:")
        if label:
            self.label.setText(label)
        self.label.setFont(Font(14))
        self.label.setStyleSheet("color: gray")

        self.lineedit = QLineEdit(self)
        self.lineedit.setFont(Font(14))
        self.lineedit.setEchoMode(QLineEdit.Password)
        self.action = QAction(QIcon(resource("eye.png")), "Toggle visibility")
        self.action.triggered.connect(self.toggle_visibility)
        self.lineedit.addAction(self.action, QLineEdit.TrailingPosition)
        self.lineedit.returnPressed.connect(self.accept)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_ok = self.button_box.button(QDialogButtonBox.Ok)
        if ok_button_text:
            self.button_ok.setText(ok_button_text)
        self.button_ok.clicked.connect(self.accept)
        self.button_cancel = self.button_box.button(QDialogButtonBox.Cancel)
        self.button_cancel.clicked.connect(self.reject)

        layout = QGridLayout(self)
        layout.addWidget(self.label, 1, 1)
        layout.addWidget(self.lineedit, 2, 1)

        if show_stats:
            self.progressbar = QProgressBar()
            self.progressbar.setMaximum(4)
            self.progressbar.setTextVisible(False)
            self.progressbar.setFixedHeight(5)
            self.progressbar.setStyleSheet(
                "QProgressBar { background-color: transparent }"
                "QProgressBar::chunk { background-color: gray }"
            )

            self.rating_label = QLabel()
            self.rating_label.setAlignment(Qt.AlignRight)

            self.time_label = QLabel()
            self.time_label.setStyleSheet("color: gray")

            layout.addWidget(self.progressbar, 3, 1)
            layout.addWidget(self.time_label, 4, 1)
            layout.addWidget(self.rating_label, 4, 1)

            self.lineedit.textChanged.connect(self.update_stats)

            self.update_color("transparent")

        if help_text:
            gbox = QGroupBox()
            gbox_layout = QGridLayout()
            gbox_label = QLabel(help_text)
            gbox_label.setWordWrap(True)
            gbox_label.setAlignment(Qt.AlignCenter)
            gbox_label.setStyleSheet("color: gray")
            gbox_layout.addWidget(gbox_label)
            gbox.setLayout(gbox_layout)
            layout.addWidget(gbox, 5, 1)

        layout.addItem(VSpacer(), 6, 1)
        layout.addWidget(self.button_box, 7, 1)

    def update_color(self, color: str) -> None:
        self.rating_label.setStyleSheet(f"QLabel {{ color: {color} }}")
        self.progressbar.setStyleSheet(
            "QProgressBar { background-color: transparent }"
            f"QProgressBar::chunk {{ background-color: {color} }}"
        )

    def toggle_visibility(self) -> None:
        if self.lineedit.echoMode() == QLineEdit.Password:
            self.lineedit.setEchoMode(QLineEdit.Normal)
        else:
            self.lineedit.setEchoMode(QLineEdit.Password)

    def update_stats(self, text: str) -> None:  # noqa: max-complexity=11 XXX
        if not text:
            self.time_label.setText("")
            self.rating_label.setText("")
            self.progressbar.setValue(0)
            return
        res = zxcvbn(text)
        t = res["crack_times_display"]["offline_slow_hashing_1e4_per_second"]
        self.time_label.setText(f"Time to crack: {t}")
        s = res["crack_times_seconds"]["offline_slow_hashing_1e4_per_second"]
        seconds = int(s)
        if seconds == 0:
            self.rating_label.setText("Very weak")
            self.update_color("lightgray")
            self.rating_label.setStyleSheet("QLabel { color: gray }")
            self.progressbar.setValue(1)
        elif seconds < 86400:  # 1 day
            self.rating_label.setText("Weak")
            self.update_color("red")
            self.progressbar.setValue(1)
        elif seconds < 2592000:  # 1 month
            self.rating_label.setText("Alright")
            self.update_color("orange")
            self.progressbar.setValue(2)
        elif seconds < 3153600000:  # 100 years
            self.rating_label.setText("Good")
            self.update_color("#9CC259")
            self.progressbar.setValue(3)
        else:  # > 100 years
            self.rating_label.setText("Excellent")
            self.update_color("#00B400")
            self.progressbar.setValue(4)
        warning = res["feedback"]["warning"]
        try:
            suggestion = "Suggestion: " + res["feedback"]["suggestions"][0]
        except IndexError:
            suggestion = None
        if warning and suggestion:
            self.rating_label.setToolTip(warning + "\n\n" + suggestion)
        elif warning:
            self.rating_label.setToolTip(warning)
        elif suggestion:
            self.rating_label.setToolTip(suggestion)
        else:
            self.rating_label.setToolTip("")

    def keyPressEvent(self, event: QEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.reject()

    @staticmethod
    def get_password(
        label: str = "",
        ok_button_text: str = "",
        help_text: str = "",
        show_stats: bool = True,
        parent: Optional[QWidget] = None,
    ) -> Tuple[str, bool]:
        dialog = PasswordDialog(
            label=label,
            ok_button_text=ok_button_text,
            help_text=help_text,
            show_stats=show_stats,
            parent=parent,
        )
        result = dialog.exec_()
        return (dialog.lineedit.text(), result)
