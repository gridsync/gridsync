from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

from humanize import naturaltime
from qtpy.QtCore import QEvent, QFileInfo, QPoint, Qt, QTimer, Slot
from qtpy.QtGui import QCursor, QIcon, QPixmap, QShowEvent
from qtpy.QtWidgets import (
    QAbstractItemView,
    QAction,
    QFileIconProvider,
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QWidget,
)

from gridsync import resource
from gridsync.desktop import open_enclosing_folder, open_path
from gridsync.gui.color import BlendedColor
from gridsync.gui.font import Font
from gridsync.gui.status import StatusPanel
from gridsync.gui.widgets import HSpacer

if TYPE_CHECKING:
    from gridsync.gui import AbstractGui
    from gridsync.tahoe import Tahoe


class HistoryItemWidget(QWidget):
    def __init__(
        self, action: str, path: str, mtime: int, parent: HistoryListWidget
    ) -> None:
        super().__init__(parent)
        # TODO: Display author/participant info?
        self.action = action
        self.path = path
        self.mtime = mtime
        self._parent = parent

        self._thumbnail_loaded = False

        self.setAutoFillBackground(True)

        self.setToolTip(
            f"{self.path}\n\n{self.action}: {time.ctime(self.mtime)}"
        )

        self.icon = QLabel()
        self.icon.setPixmap(
            QFileIconProvider().icon(QFileInfo(self.path)).pixmap(48, 48)
        )

        self.basename_label = QLabel(Path(self.path).resolve().name)
        self.basename_label.setFont(Font(11))

        self.details_label = QLabel()
        self.details_label.setFont(Font(10))
        palette = self.palette()
        dimmer_grey = BlendedColor(
            palette.text().color(), palette.base().color(), 0.6
        ).name()
        self.details_label.setStyleSheet("color: {}".format(dimmer_grey))

        self.button = QPushButton()
        self.button.setIcon(QIcon(resource("dots-horizontal-triple.png")))
        self.button.setStyleSheet("border: none;")
        self.button.clicked.connect(self._parent.on_right_click)
        self.button.hide()

        layout = QGridLayout(self)
        layout.addWidget(self.icon, 1, 1, 2, 2)
        layout.addWidget(self.basename_label, 1, 3)
        layout.addWidget(self.details_label, 2, 3)
        layout.addItem(HSpacer(), 4, 4)
        layout.addWidget(self.button, 1, 5, 2, 2)

        self.update_text()
        QTimer.singleShot(50, self.load_thumbnail)

    def update_text(self) -> None:
        self.details_label.setText(
            "{} {}".format(
                self.action.capitalize(),
                naturaltime(int(time.time() - self.mtime)),
            )
        )

    def _do_load_thumbnail(self) -> None:
        pixmap = QPixmap(self.path)
        if not pixmap.isNull():
            self.icon.setPixmap(
                pixmap.scaled(
                    48, 48, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
            )

    def load_thumbnail(self) -> None:
        if self.isVisible() and not self._thumbnail_loaded:
            self._thumbnail_loaded = True
            QTimer.singleShot(50, self._do_load_thumbnail)

    def unhighlight(self) -> None:
        self.button.hide()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self._parent.base_color)
        self.setPalette(palette)

    def enterEvent(self, _: QEvent) -> None:
        self.button.show()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self._parent.highlighted_color)
        self.setPalette(palette)
        if self._parent.highlighted and self._parent.highlighted is not self:
            try:
                self._parent.highlighted.unhighlight()
            except RuntimeError:  # Object has been deleted
                pass
        self._parent.highlighted = self


class HistoryListWidget(QListWidget):
    def __init__(
        self, gateway: Tahoe, deduplicate: bool = True, max_items: int = 30
    ) -> None:
        super().__init__()
        self.gateway = gateway
        self.deduplicate = deduplicate
        self.max_items = max_items

        palette = self.palette()
        self.base_color = palette.base().color()
        self.highlighted_color = BlendedColor(
            self.base_color, palette.highlight().color(), 0.88
        )  # Was #E6F1F7
        self.highlighted: Optional[HistoryItemWidget] = None

        self.action_icon = QIcon(resource("dots-horizontal-triple.png"))

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        # self.setStyleSheet("QListWidget::item:hover { background: #E6F1F7 }")
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.sb = self.verticalScrollBar()

        self.sb.valueChanged.connect(self.update_visible_widgets)
        self.itemDoubleClicked.connect(self.on_double_click)
        self.customContextMenuRequested.connect(self.on_right_click)

        self.gateway.monitor.check_finished.connect(
            self.update_visible_widgets
        )

        mf_monitor = self.gateway.magic_folder.monitor
        # XXX Magic-Folder does not yet send events for different
        # "kinds" of file-changes (e.g., "added" vs. "modified" vs.
        # "removed"), so just treat them all as "modified" for now.
        mf_monitor.file_added.connect(self._on_file_modified)
        mf_monitor.file_modified.connect(self._on_file_modified)
        mf_monitor.file_removed.connect(self._on_file_modified)

        mf_events = self.gateway.magic_folder.events
        mf_events.upload_finished.connect(self._on_upload_finished)
        mf_events.download_finished.connect(self._on_download_finished)

    def on_double_click(self, item: QListWidgetItem) -> None:
        w = self.itemWidget(item)
        if isinstance(w, HistoryItemWidget):
            open_enclosing_folder(w.path)

    def on_right_click(self, position: QPoint) -> None:
        if not position:
            position = self.viewport().mapFromGlobal(QCursor.pos())
        item = cast(QListWidgetItem, self.itemAt(position))
        if not item:
            return
        widget = cast(HistoryItemWidget, self.itemWidget(item))
        if not isinstance(widget, HistoryItemWidget):
            return
        menu = QMenu(self)
        open_file_action = QAction("Open file")
        open_file_action.triggered.connect(lambda: open_path(widget.path))
        menu.addAction(open_file_action)
        open_folder_action = QAction("Open enclosing folder")
        open_folder_action.triggered.connect(
            lambda: self.on_double_click(item)
        )
        menu.addAction(open_folder_action)
        menu.exec_(self.viewport().mapToGlobal(position))

    def add_item(
        self, folder: str, action: str, relpath: str, timestamp: float
    ) -> None:
        path = str(
            Path(self.gateway.magic_folder.get_directory(folder), relpath)
        )
        duplicate = None
        if self.deduplicate:
            for i in range(self.count()):
                widget = self.itemWidget(self.item(i))
                if (
                    widget
                    and isinstance(widget, HistoryItemWidget)
                    and widget.path == path
                    # and widget.data.get("member") == data.get("member")  # XXX
                ):
                    duplicate = i
                    break
        if duplicate is not None:
            item = self.takeItem(duplicate)
            if not item:
                return  # Otherwise, mypy interprets item as an Optional below
        else:
            self.takeItem(self.max_items)
            item = QListWidgetItem()
        mtime = int(timestamp)
        self.insertItem(1 - mtime, item)  # Newest on top
        custom_widget = HistoryItemWidget(action, path, mtime, self)
        item.setSizeHint(custom_widget.sizeHint())
        self.setItemWidget(item, custom_widget)
        item.setText(str(mtime))
        self.sortItems(Qt.DescendingOrder)  # Sort by mtime; newest on top

    def _on_file_added(self, folder: str, data: dict) -> None:
        self.add_item(folder, "Added", data["relpath"], data["last-updated"])

    def _on_file_modified(self, folder: str, data: dict) -> None:
        self.add_item(folder, "Updated", data["relpath"], data["last-updated"])

    def _on_file_removed(self, folder: str, data: dict) -> None:
        self.add_item(folder, "Deleted", data["relpath"], data["last-updated"])

    @Slot(str, str, float)
    def _on_upload_finished(
        self, folder: str, relpath: str, timestamp: float
    ) -> None:
        self.add_item(folder, "Uploaded", relpath, int(timestamp))

    @Slot(str, str, float)
    def _on_download_finished(
        self, folder: str, relpath: str, timestamp: float
    ) -> None:
        self.add_item(folder, "Downloaded", relpath, int(timestamp))

    def update_visible_widgets(self) -> None:
        if not self.isVisible():
            return
        rect = self.viewport().contentsRect()
        top = self.indexAt(rect.topLeft())
        if top.isValid():
            bottom = self.indexAt(rect.bottomLeft())
            if not bottom.isValid():
                bottom = self.model().index(self.count() - 1, 0)
            for index in range(top.row(), bottom.row() + 1):
                widget = self.itemWidget(self.item(index))
                if widget and isinstance(widget, HistoryItemWidget):
                    widget.update_text()
                    widget.load_thumbnail()

    def showEvent(self, _: QShowEvent) -> None:
        self.update_visible_widgets()


class HistoryView(QWidget):
    def __init__(
        self,
        gateway: Tahoe,
        gui: AbstractGui,
        deduplicate: bool = True,
        max_items: int = 30,
    ) -> None:
        super().__init__()
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(HistoryListWidget(gateway, deduplicate, max_items))
        self.status_panel = StatusPanel(gateway, gui)
        layout.addWidget(self.status_panel)
